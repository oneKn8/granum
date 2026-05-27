"""Anti-degeneracy regularization for CoEvolutionDriver (F3.1).

Covers:
  1. Mutation-count cap (writer + payer): effective = min(mutation_count,
     max(1, floor(population_size * mutation_rate_cap))).
  2. Adversary reset: every `adversary_reset_every` rounds the full payer
     population is tombstoned and re-seeded from SEEDED_PERSONAS.
  3. Constructor validation of the two new params.
  4. Backwards compatibility: existing test suite must keep passing.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.adversary.payer_agent import PayerAgent
from granum.adversary.payer_persona import SEEDED_PERSONAS
from granum.center.coevolution import CoEvolutionDriver
from granum.center.defensibility_judge import DefensibilityJudge, DefensibilityScore
from granum.center.mutation import Mutation, MutationKind
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


_GOLD_PATH = "data/aetna_cardiac/gold_appeals.jsonl"


def _writer(prompt_id: str, body: str = "writer appeal body") -> PromptVersion:
    return PromptVersion(
        prompt_id=prompt_id,
        version_id="v1",
        tags=("production",),
        body=body,
        name=f"aetna_cardiac/{prompt_id}",
    )


def _payer(prompt_id: str, persona_id: str = "strict") -> PromptVersion:
    return PromptVersion(
        prompt_id=prompt_id,
        version_id="v1",
        tags=("production",),
        body=f"payer system prompt for {persona_id}",
        name=f"aetna_cardiac_payer/baseline_{persona_id}",
    )


def _score(defensibility: int, feedback: str = "ok") -> DefensibilityScore:
    return DefensibilityScore(
        clinical_specificity=5,
        policy_citation_quality=5,
        procedural_compliance=5,
        argumentative_structure=5,
        defensibility=defensibility,
        english_feedback=feedback,
    )


def _build_mock_phoenix(
    *rounds_population: tuple[list[PromptVersion], list[PromptVersion]],
) -> AsyncMock:
    """Construct an AsyncMock PhoenixClient.

    `rounds_population` is one (writers, payers) tuple per round() call
    that the driver will make; flattened into list_active_prompts.side_effect.
    """
    mock = AsyncMock(spec=PhoenixClient)
    side_effect: list[list[PromptVersion]] = []
    for writers, payers in rounds_population:
        side_effect.append(writers)
        side_effect.append(payers)
    mock.list_active_prompts.side_effect = side_effect
    mock.tombstone.return_value = None
    mock.add_version_tag.return_value = ("production",)
    mock.add_dataset_examples.return_value = None

    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"upserted_{name}",
            version_id="v1",
            tags=tuple(tags),
            body=body,
            name=name,
        )

    mock.upsert_prompt.side_effect = _upsert
    return mock


def _build_mock_payer() -> AsyncMock:
    from granum.data.denials import Denial, DenialReason

    mock = AsyncMock(spec=PayerAgent)
    mock.deny.return_value = Denial(
        denial_id="adv_x",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t",
        submission_date="adversarial",
    )
    return mock


def _build_mock_judge(score: DefensibilityScore | None = None) -> AsyncMock:
    mock = AsyncMock(spec=DefensibilityJudge)
    mock.score.return_value = score or _score(5)
    return mock


# ---- constructor validation ----------------------------------------------


def test_invalid_mutation_rate_cap_raises():
    phoenix = _build_mock_phoenix(([_writer("w1")], [_payer("p1")]))
    payer = _build_mock_payer()
    judge = _build_mock_judge()
    for bad in (-0.1, -1.0, 1.5, 2.0):
        with pytest.raises(ValueError):
            CoEvolutionDriver(
                phoenix=phoenix,
                payer_agent=payer,
                judge=judge,
                cell="aetna_cardiac",
                gold_path=_GOLD_PATH,
                mutation_proposer=MagicMock(return_value=[]),
                mutation_rate_cap=bad,
            )


def test_invalid_adversary_reset_every_raises():
    phoenix = _build_mock_phoenix(([_writer("w1")], [_payer("p1")]))
    payer = _build_mock_payer()
    judge = _build_mock_judge()
    for bad in (0, -1, -10):
        with pytest.raises(ValueError):
            CoEvolutionDriver(
                phoenix=phoenix,
                payer_agent=payer,
                judge=judge,
                cell="aetna_cardiac",
                gold_path=_GOLD_PATH,
                mutation_proposer=MagicMock(return_value=[]),
                adversary_reset_every=bad,
            )


def test_default_mutation_rate_cap_is_0_15():
    phoenix = _build_mock_phoenix(([_writer("w1")], [_payer("p1")]))
    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=_build_mock_judge(),
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
    )
    # Access via attribute name we'll commit to in the implementation.
    assert driver._mutation_rate_cap == 0.15


def test_default_adversary_reset_every_is_5():
    phoenix = _build_mock_phoenix(([_writer("w1")], [_payer("p1")]))
    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=_build_mock_judge(),
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
    )
    assert driver._adversary_reset_every == 5


# ---- mutation cap -------------------------------------------------------


@pytest.mark.asyncio
async def test_mutation_rate_cap_below_floor_yields_one_mutant_min():
    """population=3, cap=0.15 → max(1, int(3*0.15))=max(1,0)=1 effective mutant."""
    writers = [
        _writer("w1", "winner body has MARK_W"),
        _writer("w2", "second writer body"),
        _writer("w3", "third writer body"),
    ]
    payers = [
        _payer("p1", "strict"),
        _payer("p2", "lenient"),
        _payer("p3", "formalist"),
    ]
    # Mutation proposer returns exactly the requested n=1 each call.
    writer_mut = Mutation(
        kind=MutationKind.CITATION_SWAP,
        target="MARK_W",
        replacement="REPL_W",
    )
    payer_mut = Mutation(
        kind=MutationKind.CITATION_SWAP,
        target="strict",
        replacement="VERY_STRICT",
    )

    received_n: list[int] = []

    def proposer(*, parent: str, n: int, seed=None):
        received_n.append(n)
        # Return n mutations (caller may cap)
        if "MARK_W" in parent:
            return [writer_mut] * n
        return [payer_mut] * n

    phoenix = _build_mock_phoenix((writers, payers))
    # Make w1 win and p1 win by score arrangement; with 3x3=9 pairs, use uniform scores
    # that still produce a unique winner. Use 9 distinct scores ordered so w1 leads.
    scores = [
        _score(9), _score(9), _score(9),  # w1: mean 9
        _score(4), _score(5), _score(5),  # w2: mean ~4.67
        _score(4), _score(4), _score(5),  # w3: mean ~4.33
    ]
    judge = _build_mock_judge()
    judge.score.side_effect = scores

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=proposer,
        mutation_count=2,
        mutation_rate_cap=0.15,
    )

    await driver.round()

    # Proposer should have been called twice (writer + payer), each with n=1.
    assert received_n == [1, 1]

    # Exactly two mutant upserts: 1 writer + 1 payer.
    upsert_names = [c.kwargs["name"] for c in phoenix.upsert_prompt.await_args_list]
    writer_mutant_upserts = [
        n for n in upsert_names if n.startswith("aetna_cardiac/bcell_mut_")
    ]
    payer_mutant_upserts = [
        n for n in upsert_names if n.startswith("aetna_cardiac_payer/mut_")
    ]
    assert len(writer_mutant_upserts) == 1
    assert len(payer_mutant_upserts) == 1


@pytest.mark.asyncio
async def test_mutation_count_caps_to_effective_when_proposer_returns_more():
    """population=20, cap=0.15 → max(1, int(20*0.15))=3; mutation_count=5 → effective=3."""
    writers = [_writer(f"w{i}", f"body w{i} MARK_W") for i in range(20)]
    payers = [
        _payer(f"p{i}", "strict" if i % 2 == 0 else "lenient") for i in range(20)
    ]
    # Make w0 the clear winner with high scores in all of its pairs.
    scores: list[DefensibilityScore] = []
    for w_i in range(20):
        for _p_j in range(20):
            scores.append(_score(9 if w_i == 0 else 3))

    received_n: list[int] = []

    def proposer(*, parent: str, n: int, seed=None):
        received_n.append(n)
        # Return exactly n mutations.
        mut = Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="MARK_W" if "MARK_W" in parent else "strict",
            replacement="REPL",
        )
        return [mut] * n

    phoenix = _build_mock_phoenix((writers, payers))
    judge = _build_mock_judge()
    judge.score.side_effect = scores

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=proposer,
        mutation_count=5,
        mutation_rate_cap=0.15,
    )

    await driver.round()

    # Both proposer calls must use n=3, not 5.
    assert received_n == [3, 3]


# ---- adversary reset ----------------------------------------------------


@pytest.mark.asyncio
async def test_adversary_reset_fires_at_correct_round():
    """With adversary_reset_every=5, reset must fire ONLY at round_index=4."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    # Driver makes 5 round() calls. Population is the same each round (mocked).
    phoenix = _build_mock_phoenix(*[(writers, payers)] * 5)
    judge = _build_mock_judge(_score(7))

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
        adversary_reset_every=5,
    )

    outcomes = []
    for _ in range(5):
        outcomes.append(await driver.round())

    fired = [o.adversary_reset_fired for o in outcomes]
    assert fired == [False, False, False, False, True]


@pytest.mark.asyncio
async def test_adversary_reset_does_not_fire_before_threshold():
    """Run 4 rounds with adversary_reset_every=5; no reset should fire."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    phoenix = _build_mock_phoenix(*[(writers, payers)] * 4)
    judge = _build_mock_judge(_score(7))

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
        adversary_reset_every=5,
    )

    outcomes = [await driver.round() for _ in range(4)]
    assert all(not o.adversary_reset_fired for o in outcomes)

    # No baseline_<persona> upserts at all (since no reset fired).
    upsert_names = [c.kwargs["name"] for c in phoenix.upsert_prompt.await_args_list]
    baseline_upserts = [
        n for n in upsert_names
        if n.startswith("aetna_cardiac_payer/baseline_")
    ]
    assert baseline_upserts == []


@pytest.mark.asyncio
async def test_adversary_reset_tombstones_full_payer_population():
    """adversary_reset_every=1: reset every round. Both payers must be tombstoned."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict"), _payer("p2", "lenient")]
    phoenix = _build_mock_phoenix((writers, payers))
    # Pair scores: (w1,p1), (w1,p2). Need a winner among payers — give p1 worse-for-writer.
    scores = [_score(3), _score(9)]
    judge = _build_mock_judge()
    judge.score.side_effect = scores

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
        adversary_reset_every=1,
    )

    outcome = await driver.round()
    assert outcome.adversary_reset_fired is True

    # All tombstone calls — collect unique prompt_ids.
    tombstoned = {c.args[0] for c in phoenix.tombstone.await_args_list}
    # Both p1 and p2 must appear in the tombstoned set (full pop wiped).
    assert "p1" in tombstoned
    assert "p2" in tombstoned


@pytest.mark.asyncio
async def test_adversary_reset_upserts_five_seeded_personas():
    """adversary_reset_every=1: after reset, all 5 SEEDED_PERSONAS upserted."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    phoenix = _build_mock_phoenix((writers, payers))
    judge = _build_mock_judge(_score(7))

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
        adversary_reset_every=1,
    )

    await driver.round()

    upsert_names = [c.kwargs["name"] for c in phoenix.upsert_prompt.await_args_list]
    expected_baseline_names = {
        f"aetna_cardiac_payer/baseline_{p.persona_id}"
        for p in SEEDED_PERSONAS
    }
    actual_baseline_names = {
        n for n in upsert_names
        if n.startswith("aetna_cardiac_payer/baseline_")
    }
    assert actual_baseline_names == expected_baseline_names
    # And the count of baseline upserts is exactly 5 (one per persona).
    baseline_count = sum(
        1 for n in upsert_names
        if n.startswith("aetna_cardiac_payer/baseline_")
    )
    assert baseline_count == 5


@pytest.mark.asyncio
async def test_round_index_increments_after_reset():
    """Reset firing must not block round_index increment."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    phoenix = _build_mock_phoenix((writers, payers), (writers, payers))
    judge = _build_mock_judge(_score(7))

    driver = CoEvolutionDriver(
        phoenix=phoenix,
        payer_agent=_build_mock_payer(),
        judge=judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
        adversary_reset_every=1,
    )

    first = await driver.round()
    second = await driver.round()
    assert first.round_index == 0
    assert second.round_index == 1
    assert first.adversary_reset_fired is True
    assert second.adversary_reset_fired is True
