"""Co-evolution driver — one Red Queen round per cell.

Mirrors GerminalCycle tests but covers dual-population evolution:
writers + payers, triangular tournament, both-side apoptosis and promotion,
mutations on both winners, dataset writeback to a co-evolution dataset.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.adversary.payer_agent import PayerAgent
from granum.center.coevolution import CoEvolutionDriver, CoEvolutionRoundResult
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


def _payer(prompt_id: str, persona_id: str = "strict", index: int | None = None) -> PromptVersion:
    if index is None:
        suffix = f"baseline_{persona_id}"
    else:
        suffix = f"mut_{persona_id}_{index}"
    return PromptVersion(
        prompt_id=prompt_id,
        version_id="v1",
        tags=("production",),
        body=f"payer system prompt for {persona_id}",
        name=f"aetna_cardiac_payer/{suffix}",
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


def _make_driver(
    *,
    writers: list[PromptVersion],
    payers: list[PromptVersion],
    score_side_effect: list[DefensibilityScore] | None = None,
    mutation_proposer=None,
    mutation_count: int = 2,
) -> tuple[CoEvolutionDriver, AsyncMock, AsyncMock, AsyncMock]:
    mock_phoenix = AsyncMock(spec=PhoenixClient)
    mock_phoenix.list_active_prompts.side_effect = [writers, payers]
    mock_phoenix.tombstone.return_value = None
    mock_phoenix.add_version_tag.return_value = ("production",)
    mock_phoenix.add_dataset_examples.return_value = None
    # upsert_prompt returns a fresh PromptVersion echoing the inputs
    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"upserted_{name}",
            version_id="v1",
            tags=tuple(tags),
            body=body,
            name=name,
        )
    mock_phoenix.upsert_prompt.side_effect = _upsert

    mock_payer = AsyncMock(spec=PayerAgent)
    # Default denial response — irrelevant unless test overrides
    from granum.data.denials import Denial, DenialReason
    mock_payer.deny.return_value = Denial(
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

    mock_judge = AsyncMock(spec=DefensibilityJudge)
    if score_side_effect is not None:
        mock_judge.score.side_effect = score_side_effect
    else:
        mock_judge.score.return_value = _score(5)

    if mutation_proposer is None:
        mutation_proposer = MagicMock(return_value=[])

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=mutation_proposer,
        mutation_count=mutation_count,
    )
    return driver, mock_phoenix, mock_payer, mock_judge


@pytest.mark.asyncio
async def test_full_round_promotes_both_winners_tombstones_both_losers():
    writers = [_writer("w1", "winning body w1"), _writer("w2", "losing body w2")]
    payers = [_payer("p1", "strict"), _payer("p2", "lenient")]
    # pair order: (w1,p1), (w1,p2), (w2,p1), (w2,p2)
    # w1: 9, 7 → mean 8.0 winner; w2: 4, 4 → mean 4.0 loser
    # p1 inverse: (10-9 + 10-4)/2 = 3.5 ; p2 inverse: (10-7 + 10-4)/2 = 4.5 → p2 wins?
    # We want p1 to win — flip the scores so p1 inverse > p2 inverse.
    # Use w1: 9,7 (w1 wins by mean 8), w2: 4,8 → mean 6 still loses; p1 inverse mean (1+6)/2=3.5,
    # p2 inverse mean (3+2)/2=2.5 → p1 wins (correct).
    scores = [_score(9), _score(7), _score(4), _score(8)]
    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers, payers=payers, score_side_effect=scores
    )

    outcome = await driver.round()

    assert isinstance(outcome, CoEvolutionRoundResult)
    assert outcome.writer_winner_id == "w1"
    assert outcome.payer_winner_id == "p1"

    # Two tombstones: w2 + p2.
    assert mock_phoenix.tombstone.await_count == 2
    tombstoned_ids = {call.args[0] for call in mock_phoenix.tombstone.await_args_list}
    assert tombstoned_ids == {"w2", "p2"}

    # Two production tags — one for each winner.
    assert mock_phoenix.add_version_tag.await_count == 2
    promoted = {(c.args[0], c.args[2]) for c in mock_phoenix.add_version_tag.await_args_list}
    assert promoted == {("w1", "production"), ("p1", "production")}

    # Dataset writeback to co-evolution dataset, once.
    mock_phoenix.add_dataset_examples.assert_awaited_once()
    ds_kwargs = mock_phoenix.add_dataset_examples.await_args.kwargs
    assert ds_kwargs["dataset_name"] == "granum/aetna_cardiac/coevolution"


@pytest.mark.asyncio
async def test_round_raises_when_writer_population_empty():
    driver, mock_phoenix, _, _ = _make_driver(
        writers=[], payers=[_payer("p1", "strict")]
    )
    with pytest.raises(RuntimeError, match="empty writer population"):
        await driver.round()


@pytest.mark.asyncio
async def test_round_raises_when_payer_population_empty():
    driver, mock_phoenix, _, _ = _make_driver(
        writers=[_writer("w1")], payers=[]
    )
    with pytest.raises(RuntimeError, match="empty payer population"):
        await driver.round()


@pytest.mark.asyncio
async def test_writer_mutations_spawned_from_writer_winner_body():
    writers = [_writer("w1", "winner body contains MARK_W here")]
    payers = [_payer("p1", "strict")]
    # mutation proposer returns 2 valid writer mutations targeting MARK_W
    writer_mutations = [
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="MARK_W",
            replacement="REPL_W_1",
        ),
        Mutation(
            kind=MutationKind.PARAGRAPH_REFRAME,
            target="MARK_W",
            replacement="REPL_W_2",
        ),
    ]
    # Note: payer mutations applied to payer system_prompt body. We do not
    # want them to apply in this test, so make them target a non-existent
    # string — they will be skipped silently.
    payer_mutations = [
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="__NOPE__",
            replacement="x",
        ),
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="__NOPE__",
            replacement="y",
        ),
    ]

    def proposer(*, parent: str, n: int, seed=None):
        # Writer parent contains MARK_W; payer parent does not.
        if "MARK_W" in parent:
            return writer_mutations
        return payer_mutations

    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(8)],
        mutation_proposer=proposer,
        mutation_count=2,
    )
    await driver.round()

    # Pick out writer mutant upserts
    upsert_calls = mock_phoenix.upsert_prompt.await_args_list
    writer_mutant_names = [
        c.kwargs["name"] for c in upsert_calls
        if c.kwargs["name"].startswith("aetna_cardiac/bcell_mut_")
    ]
    assert writer_mutant_names == [
        "aetna_cardiac/bcell_mut_w1_0",
        "aetna_cardiac/bcell_mut_w1_1",
    ]


@pytest.mark.asyncio
async def test_payer_mutations_spawned_from_payer_winner_body():
    writers = [_writer("w1", "winner body has MARK_W")]
    payers = [_payer("p1", "strict")]
    # Writer mutations target a non-existent string (skipped).
    # Payer mutations target the payer body, which is
    # "payer system prompt for strict".
    writer_mutations = [
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="__NOPE__",
            replacement="x",
        ),
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="__NOPE__",
            replacement="y",
        ),
    ]
    payer_mutations = [
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="strict",
            replacement="VERY_STRICT_A",
        ),
        Mutation(
            kind=MutationKind.CITATION_SWAP,
            target="prompt",
            replacement="POLICY_B",
        ),
    ]

    def proposer(*, parent: str, n: int, seed=None):
        if "MARK_W" in parent:
            return writer_mutations
        return payer_mutations

    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(8)],
        mutation_proposer=proposer,
        mutation_count=2,
    )
    await driver.round()

    upsert_calls = mock_phoenix.upsert_prompt.await_args_list
    payer_mutant_names = [
        c.kwargs["name"] for c in upsert_calls
        if c.kwargs["name"].startswith("aetna_cardiac_payer/mut_")
    ]
    assert payer_mutant_names == [
        "aetna_cardiac_payer/mut_strict_0",
        "aetna_cardiac_payer/mut_strict_1",
    ]


@pytest.mark.asyncio
async def test_dataset_writeback_includes_defensibility_composite_and_feedback():
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    judge_score = DefensibilityScore(
        clinical_specificity=6,
        policy_citation_quality=7,
        procedural_compliance=8,
        argumentative_structure=9,
        defensibility=10,
        english_feedback="strong defense across all axes",
    )
    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[judge_score],
    )
    outcome = await driver.round()

    examples = mock_phoenix.add_dataset_examples.await_args.kwargs["examples"]
    assert len(examples) == 1
    ex = examples[0]
    assert ex["defensibility_composite"] == pytest.approx(judge_score.composite)
    assert ex["english_feedback"] == "strong defense across all axes"
    assert outcome.defensibility_composite == pytest.approx(judge_score.composite)
    assert outcome.english_feedback == "strong defense across all axes"


@pytest.mark.asyncio
async def test_round_index_increments_after_successful_round():
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    mock_phoenix = AsyncMock(spec=PhoenixClient)
    # list_active called 4 times across two rounds
    mock_phoenix.list_active_prompts.side_effect = [
        writers, payers, writers, payers,
    ]
    mock_phoenix.tombstone.return_value = None
    mock_phoenix.add_version_tag.return_value = ("production",)
    mock_phoenix.add_dataset_examples.return_value = None
    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"u_{name}", version_id="v1", tags=tuple(tags),
            body=body, name=name,
        )
    mock_phoenix.upsert_prompt.side_effect = _upsert

    mock_payer = AsyncMock(spec=PayerAgent)
    from granum.data.denials import Denial, DenialReason
    mock_payer.deny.return_value = Denial(
        denial_id="d", payer="aetna", diagnosis="cardiac",
        cpt_code="93306", icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t", submission_date="adversarial",
    )

    mock_judge = AsyncMock(spec=DefensibilityJudge)
    mock_judge.score.return_value = _score(7)

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
        mutation_count=0,
    )

    first = await driver.round()
    second = await driver.round()
    assert first.round_index == 0
    assert second.round_index == 1


@pytest.mark.asyncio
async def test_failed_mutation_is_skipped_not_propagated():
    writers = [_writer("w1", "body w1")]
    payers = [_payer("p1", "strict")]
    # Single mutation targeting a string NOT in the writer body or payer body.
    bad_mutation = Mutation(
        kind=MutationKind.CITATION_SWAP,
        target="DOES_NOT_EXIST",
        replacement="x",
    )

    def proposer(*, parent: str, n: int, seed=None):
        return [bad_mutation]

    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(8)],
        mutation_proposer=proposer,
        mutation_count=1,
    )
    # Should not raise.
    outcome = await driver.round()
    assert outcome.writer_mutant_ids == ()
    assert outcome.payer_mutant_ids == ()
    # No mutant upserts attempted (both writer & payer mutations skipped).
    upsert_calls = mock_phoenix.upsert_prompt.await_args_list
    assert all(
        not c.kwargs["name"].startswith("aetna_cardiac/bcell_mut_")
        and not c.kwargs["name"].startswith("aetna_cardiac_payer/mut_")
        for c in upsert_calls
    )
