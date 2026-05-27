"""Phase 3 integration test — 5 co-evolution rounds end-to-end.

Exercises the full CoEvolutionDriver pipeline through 5 rounds with mocked
Phoenix + LLM + payer agent, then asserts the Phase 3 gate criteria:

  (a) 5 rounds complete without exception
  (b) Neither population goes extinct — every round produces winners
  (c) Defensibility composite climbs monotonically across rounds
  (d) Mutation rate cap enforced (n requested = effective per round)
  (e) Round 5 (round_index=4) fires adversary reset (5 baseline upserts)
  (f) Dataset writeback called once per round
  (g) OTel span `granum.coevolution.round` emitted per round
  (h) round_index increments monotonically 0 -> 4
"""
from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from granum.adversary.payer_agent import PayerAgent
from granum.adversary.payer_persona import SEEDED_PERSONAS
from granum.center.coevolution import CoEvolutionDriver, CoEvolutionRoundResult
from granum.center.defensibility_judge import DefensibilityJudge, DefensibilityScore
from granum.center.mutation import Mutation, MutationKind
from granum.data.denials import Denial, DenialReason
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


_GOLD_PATH = "data/aetna_cardiac/gold_appeals.jsonl"
_NUM_ROUNDS = 5
_NUM_WRITERS = 3
_NUM_PAYERS = 5
_PAIRS_PER_ROUND = _NUM_WRITERS * _NUM_PAYERS  # 15


# ---- fixtures ------------------------------------------------------------


def _score(value: int, feedback: str = "ok") -> DefensibilityScore:
    """Uniform-axis defensibility score so composite == value."""
    return DefensibilityScore(
        clinical_specificity=value,
        policy_citation_quality=value,
        procedural_compliance=value,
        argumentative_structure=value,
        defensibility=value,
        english_feedback=feedback,
    )


def _writer_pop() -> list[PromptVersion]:
    """3 writer prompts; bodies share the mutation target 'Aetna CPB 0119'."""
    return [
        PromptVersion(
            prompt_id=f"w{i}",
            version_id="v1",
            tags=("production",),
            body=(
                f"Per Aetna CPB 0119 section IV.A appeal {i}. "
                f"ACC/AHA 2021 supports. Appeal deadline: 30 days."
            ),
            name=f"aetna_cardiac/bcell_{i}",
        )
        for i in range(_NUM_WRITERS)
    ]


def _payer_pop() -> list[PromptVersion]:
    """5 payer prompts — one baseline per SEEDED persona."""
    return [
        PromptVersion(
            prompt_id=f"p_{persona.persona_id}",
            version_id="v1",
            tags=("production",),
            body=persona.system_prompt,
            name=f"aetna_cardiac_payer/baseline_{persona.persona_id}",
        )
        for persona in SEEDED_PERSONAS
    ]


def _make_proposer() -> Callable:
    """Mutation proposer that yields writer-applicable mutations.

    Writer bodies contain 'Aetna CPB 0119' so the CITATION_SWAP applies.
    Payer bodies do NOT contain that target so payer mutations skip
    silently in apply_mutation (expected — we only assert writer mutants).
    """

    def proposer(*, parent: str, n: int, seed: int | None = None) -> list[Mutation]:
        return [
            Mutation(
                kind=MutationKind.CITATION_SWAP,
                target="Aetna CPB 0119",
                replacement=f"Aetna CPB 028{i}",
            )
            for i in range(n)
        ]

    return proposer


def _make_phoenix(writers: list[PromptVersion], payers: list[PromptVersion]) -> AsyncMock:
    """AsyncMock PhoenixClient that returns same writer/payer pops each call.

    The driver does not re-query mid-round; tombstone/upsert are no-ops on
    the mock. Using a lambda side_effect keeps the mock stable across all
    5 rounds without needing a precomputed flat list.
    """
    mock = AsyncMock(spec=PhoenixClient)

    async def _list_active(*, name_prefix: str) -> list[PromptVersion]:
        if name_prefix == "aetna_cardiac/":
            return writers
        if name_prefix == "aetna_cardiac_payer/":
            return payers
        return []

    mock.list_active_prompts.side_effect = _list_active
    mock.tombstone.return_value = None
    mock.add_version_tag.return_value = ("production",)
    mock.add_dataset_examples.return_value = None

    async def _upsert(*, name: str, body: str, tags=("experimental",)) -> PromptVersion:
        return PromptVersion(
            prompt_id=f"upserted_{name}",
            version_id="v1",
            tags=tuple(tags),
            body=body,
            name=name,
        )

    mock.upsert_prompt.side_effect = _upsert
    return mock


def _make_payer_agent() -> AsyncMock:
    mock = AsyncMock(spec=PayerAgent)
    mock.deny.return_value = Denial(
        denial_id="adv_x",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text=(
            "Denial reason: NMN. Per policy CPB 0119. "
            "Appeal rights: 30 days."
        ),
        submission_date="adversarial",
    )
    return mock


def _make_judge(scripted_axis_per_round: list[int]) -> AsyncMock:
    """Judge mock returning scores so winner composite climbs across rounds.

    Each pair score has all 5 axes set to the round's scripted value, so the
    composite (mean of axes) equals that value. With 15 pairs per round and
    5 rounds, returns 75 DefensibilityScore objects in order.
    """
    assert len(scripted_axis_per_round) == _NUM_ROUNDS
    mock = AsyncMock(spec=DefensibilityJudge)
    scripted: list[DefensibilityScore] = []
    for round_value in scripted_axis_per_round:
        for _ in range(_PAIRS_PER_ROUND):
            scripted.append(
                _score(round_value, feedback=f"round_composite={round_value}")
            )
    mock.score.side_effect = scripted
    return mock


def _make_driver(
    *,
    phoenix: AsyncMock,
    payer_agent: AsyncMock,
    judge: AsyncMock,
    mutation_count: int = 2,
) -> CoEvolutionDriver:
    return CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=payer_agent,
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=_make_proposer(),
        mutation_count=mutation_count,
        mutation_rate_cap=0.15,
        adversary_reset_every=5,
    )


async def _run_five_rounds(
    scripted_axis_per_round: list[int],
    *,
    proposer: Callable | None = None,
) -> tuple[list[CoEvolutionRoundResult], AsyncMock, MagicMock]:
    """Run 5 rounds end-to-end. Returns (outcomes, phoenix_mock, proposer_mock)."""
    writers = _writer_pop()
    payers = _payer_pop()
    phoenix = _make_phoenix(writers, payers)
    payer_agent = _make_payer_agent()
    judge = _make_judge(scripted_axis_per_round)

    # Wrap proposer in MagicMock so we can inspect call_args.
    proposer_impl = proposer or _make_proposer()
    proposer_mock = MagicMock(side_effect=proposer_impl)

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=payer_agent,
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=proposer_mock,
        mutation_count=2,
        mutation_rate_cap=0.15,
        adversary_reset_every=5,
    )

    outcomes: list[CoEvolutionRoundResult] = []
    for _ in range(_NUM_ROUNDS):
        outcomes.append(await driver.round())
    return outcomes, phoenix, proposer_mock


# ---- gate (a): 5 rounds complete without exception ----------------------


@pytest.mark.asyncio
async def test_five_rounds_complete_without_exception():
    outcomes, _, _ = await _run_five_rounds([5, 5, 6, 7, 8])
    assert len(outcomes) == _NUM_ROUNDS
    assert all(isinstance(o, CoEvolutionRoundResult) for o in outcomes)


# ---- gate (b): neither population goes extinct --------------------------


@pytest.mark.asyncio
async def test_neither_population_goes_extinct_across_rounds():
    outcomes, _, _ = await _run_five_rounds([5, 5, 6, 7, 8])
    for o in outcomes:
        assert o.writer_winner_id != ""
        assert o.payer_winner_id != ""


# ---- gate (c): defensibility climbs across rounds -----------------------


@pytest.mark.asyncio
async def test_defensibility_climbs_across_rounds():
    """Scripted scores produce per-round composite = [5, 5, 6, 7, 8].

    Monotonic non-decreasing across the full sequence — verifies that the
    judge -> tournament -> outcome composite wiring carries score values
    through the pipeline without dropping them.
    """
    scripted = [5, 5, 6, 7, 8]
    outcomes, _, _ = await _run_five_rounds(scripted)
    composites = [o.defensibility_composite for o in outcomes]
    assert composites == [pytest.approx(float(v)) for v in scripted]
    # Monotonic non-decreasing — strict climb at rounds 2, 3, 4.
    for prev, cur in zip(composites, composites[1:]):
        assert cur >= prev


# ---- gate (d): mutation rate cap enforced -------------------------------


@pytest.mark.asyncio
async def test_mutation_rate_cap_enforced_across_rounds():
    """pop=3 writers, pop=5 payers, cap=0.15.

    Writer effective: max(1, int(3 * 0.15)) = max(1, 0) = 1.
    Payer effective: max(1, int(5 * 0.15)) = max(1, 0) = 1.
    With mutation_count=2 and cap=1, proposer must always be called with n=1.
    """
    _, phoenix, proposer_mock = await _run_five_rounds([5, 5, 6, 7, 8])

    # Proposer called twice per round (writer + payer) -> 10 calls total.
    assert proposer_mock.call_count == _NUM_ROUNDS * 2
    for call in proposer_mock.call_args_list:
        assert call.kwargs["n"] == 1

    # Writer-mutant upserts per round <= 1 (cap). Payer mutations target
    # 'Aetna CPB 0119' which is not in payer bodies -> skipped silently.
    upsert_names = [c.kwargs["name"] for c in phoenix.upsert_prompt.await_args_list]
    writer_mutant_upserts = [
        n for n in upsert_names if n.startswith("aetna_cardiac/bcell_mut_")
    ]
    # 5 rounds * at most 1 writer mutant each = <= 5.
    assert len(writer_mutant_upserts) <= _NUM_ROUNDS
    # And actually equal to 5 since each writer mutation does apply.
    assert len(writer_mutant_upserts) == _NUM_ROUNDS


# ---- gate (e): round 5 triggers adversary reset -------------------------


@pytest.mark.asyncio
async def test_round_5_triggers_adversary_reset():
    """adversary_reset_every=5 -> fires ONLY at round_index=4 in this run."""
    outcomes, phoenix, _ = await _run_five_rounds([5, 5, 6, 7, 8])
    fired = [o.adversary_reset_fired for o in outcomes]
    assert fired == [False, False, False, False, True]

    # 5 baseline upserts (one per SEEDED persona) issued on round 5.
    upsert_names = [c.kwargs["name"] for c in phoenix.upsert_prompt.await_args_list]
    baseline_upserts = [
        n for n in upsert_names
        if n.startswith("aetna_cardiac_payer/baseline_")
    ]
    expected = {
        f"aetna_cardiac_payer/baseline_{p.persona_id}" for p in SEEDED_PERSONAS
    }
    assert set(baseline_upserts) == expected
    assert len(baseline_upserts) == len(SEEDED_PERSONAS)


# ---- gate (f): dataset writeback called once per round ------------------


@pytest.mark.asyncio
async def test_dataset_writeback_called_once_per_round():
    _, phoenix, _ = await _run_five_rounds([5, 5, 6, 7, 8])
    assert phoenix.add_dataset_examples.await_count == _NUM_ROUNDS
    # All writebacks target the co-evolution dataset for this cell.
    for call in phoenix.add_dataset_examples.await_args_list:
        assert call.kwargs["dataset_name"] == "granum/aetna_cardiac/coevolution"


# ---- gate (g): OTel span emitted per round ------------------------------


@pytest.mark.asyncio
async def test_otel_span_emitted_per_round():
    """Each round() must emit a `granum.coevolution.round` span.

    Sets up an InMemorySpanExporter on a fresh TracerProvider, runs 5
    rounds, then counts spans by name. We restore the original provider
    afterwards to avoid leaking state into other tests.
    """
    original_provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    test_provider = TracerProvider()
    test_provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(test_provider)
    try:
        # Re-import the module-level tracer so it binds to the new provider.
        # In coevolution.py, `_tracer = trace.get_tracer(__name__)` is
        # evaluated at import time. The underlying TracerProvider it
        # delegates to is the global singleton — swapping the global
        # provider redirects new spans to our exporter.
        await _run_five_rounds([5, 5, 6, 7, 8])
        finished = exporter.get_finished_spans()
        round_spans = [s for s in finished if s.name == "granum.coevolution.round"]
        assert len(round_spans) == _NUM_ROUNDS
    finally:
        trace.set_tracer_provider(original_provider)
        exporter.shutdown()


# ---- gate (h): round_index increments monotonically ---------------------


@pytest.mark.asyncio
async def test_round_index_increments_monotonically():
    outcomes, _, _ = await _run_five_rounds([5, 5, 6, 7, 8])
    indices = [o.round_index for o in outcomes]
    assert indices == list(range(_NUM_ROUNDS))
