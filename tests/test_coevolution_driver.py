"""Co-evolution driver — one Red Queen round per cell.

Mirrors GerminalCycle tests but covers dual-population evolution:
writers + payers, triangular tournament, both-side apoptosis and promotion,
mutations on both winners, dataset writeback to a co-evolution dataset.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.adversary.payer_agent import PayerAgent
from granum.center.coevolution import (
    CoEvolutionDriver,
    CoEvolutionRoundResult,
    _extract_persona_id,
)
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


def _antigen():
    """A minimal antigen Denial writers draft a real appeal against."""
    from granum.data.denials import Denial, DenialReason

    return Denial(
        denial_id="antigen_x",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="antigen denial text",
        submission_date="adversarial",
    )


def _make_driver(
    *,
    writers: list[PromptVersion],
    payers: list[PromptVersion],
    score_side_effect: list[DefensibilityScore] | None = None,
    mutation_proposer=None,
    mutation_count: int = 2,
    prompt_mutator=None,
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

    # Generate-then-judge: each writer drafts a real appeal from its system
    # prompt + the antigen before scoring. The mock generator echoes the writer
    # body so tests can assert the GENERATED text (not the prompt) reaches the
    # payer/judge. Exposed on driver._appeal_generator for direct inspection.
    mock_appeal_generator = AsyncMock(
        side_effect=lambda writer_body, antigen: f"GENERATED APPEAL for {writer_body}"
    )

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=mutation_proposer,
        mutation_count=mutation_count,
        appeal_generator=mock_appeal_generator,
        antigen=_antigen(),
        prompt_mutator=prompt_mutator,
    )
    return driver, mock_phoenix, mock_payer, mock_judge


@pytest.mark.asyncio
async def test_generated_appeal_flows_to_payer_and_judge_not_prompt_body():
    """The fix: writers draft a real appeal from their system prompt + antigen;
    that GENERATED letter (not the writer prompt body) is what the payer attacks
    and the judge scores. One appeal per writer, reused across all payers."""
    writers = [_writer("w1", "SYSTEM PROMPT w1"), _writer("w2", "SYSTEM PROMPT w2")]
    payers = [_payer("p1", "strict"), _payer("p2", "lenient")]
    driver, _, mock_payer, mock_judge = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(5), _score(5), _score(5), _score(5)],
    )

    await driver.round()

    # ONE appeal per writer (2 generations), reused across 2 payers each.
    assert driver._appeal_generator.await_count == 2

    deny_appeals = {c.kwargs["appeal"] for c in mock_payer.deny.await_args_list}
    assert deny_appeals == {
        "GENERATED APPEAL for SYSTEM PROMPT w1",
        "GENERATED APPEAL for SYSTEM PROMPT w2",
    }
    judged = {c.kwargs["candidate_appeal"] for c in mock_judge.score.await_args_list}
    assert judged == {
        "GENERATED APPEAL for SYSTEM PROMPT w1",
        "GENERATED APPEAL for SYSTEM PROMPT w2",
    }
    # The raw writer system prompt never reaches deny()/score().
    assert "SYSTEM PROMPT w1" not in deny_appeals
    assert "SYSTEM PROMPT w2" not in judged


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
async def test_round_raises_when_writer_population_empty(monkeypatch):
    """After all retry attempts, still-empty writer population raises RuntimeError."""
    monkeypatch.setenv("GRANUM_COEVO_LOAD_ATTEMPTS", "2")
    writers = []
    payer_list = [_payer("p1", "strict")]

    # Build a driver manually so we can supply a side_effect function.
    mock_phoenix = AsyncMock(spec=PhoenixClient)
    # Writer prefix always returns empty; payer prefix returns payer_list.
    def _list_active(*, name_prefix):
        if name_prefix.startswith("aetna_cardiac/"):
            return writers
        return payer_list
    mock_phoenix.list_active_prompts.side_effect = _list_active
    mock_phoenix.tombstone.return_value = None
    mock_phoenix.add_version_tag.return_value = ("production",)
    mock_phoenix.add_dataset_examples.return_value = None
    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"upserted_{name}", version_id="v1",
            tags=tuple(tags), body=body, name=name,
        )
    mock_phoenix.upsert_prompt.side_effect = _upsert

    from unittest.mock import patch
    mock_payer = AsyncMock(spec=PayerAgent)
    from granum.data.denials import Denial, DenialReason
    mock_payer.deny.return_value = Denial(
        denial_id="adv_x", payer="aetna", diagnosis="cardiac",
        cpt_code="93306", icd10_code="I25.10", patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t", submission_date="adversarial",
    )
    mock_judge = AsyncMock(spec=DefensibilityJudge)
    mock_judge.score.return_value = _score(5)

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
    )

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(RuntimeError, match="empty writer population"):
            await driver.round()


@pytest.mark.asyncio
async def test_round_raises_when_payer_population_empty(monkeypatch):
    """After all retry attempts, still-empty payer population raises RuntimeError."""
    monkeypatch.setenv("GRANUM_COEVO_LOAD_ATTEMPTS", "2")
    writer_list = [_writer("w1")]
    payers = []

    mock_phoenix = AsyncMock(spec=PhoenixClient)
    # Payer prefix always returns empty; writer prefix returns writer_list.
    def _list_active(*, name_prefix):
        if name_prefix.startswith("aetna_cardiac_payer/"):
            return payers
        return writer_list
    mock_phoenix.list_active_prompts.side_effect = _list_active
    mock_phoenix.tombstone.return_value = None
    mock_phoenix.add_version_tag.return_value = ("production",)
    mock_phoenix.add_dataset_examples.return_value = None
    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"upserted_{name}", version_id="v1",
            tags=tuple(tags), body=body, name=name,
        )
    mock_phoenix.upsert_prompt.side_effect = _upsert

    mock_payer = AsyncMock(spec=PayerAgent)
    from granum.data.denials import Denial, DenialReason
    mock_payer.deny.return_value = Denial(
        denial_id="adv_x", payer="aetna", diagnosis="cardiac",
        cpt_code="93306", icd10_code="I25.10", patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t", submission_date="adversarial",
    )
    mock_judge = AsyncMock(spec=DefensibilityJudge)
    mock_judge.score.return_value = _score(5)

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
    )

    from unittest.mock import patch
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(RuntimeError, match="empty payer population"):
            await driver.round()


@pytest.mark.asyncio
async def test_population_load_retries_on_transient_empty_then_succeeds(monkeypatch):
    """Payer prefix returns [] once then the real list; round() proceeds without raising."""
    monkeypatch.setenv("GRANUM_COEVO_LOAD_ATTEMPTS", "8")
    writer_list = [_writer("w1")]
    payer_list = [_payer("p1", "strict")]
    payer_call_count = {"n": 0}

    mock_phoenix = AsyncMock(spec=PhoenixClient)

    def _list_active(*, name_prefix):
        if name_prefix.startswith("aetna_cardiac_payer/"):
            payer_call_count["n"] += 1
            # First call returns empty (transient); subsequent calls return real list.
            if payer_call_count["n"] == 1:
                return []
            return payer_list
        return writer_list
    mock_phoenix.list_active_prompts.side_effect = _list_active
    mock_phoenix.tombstone.return_value = None
    mock_phoenix.add_version_tag.return_value = ("production",)
    mock_phoenix.add_dataset_examples.return_value = None
    async def _upsert(*, name, body, tags=("experimental",)):
        return PromptVersion(
            prompt_id=f"upserted_{name}", version_id="v1",
            tags=tuple(tags), body=body, name=name,
        )
    mock_phoenix.upsert_prompt.side_effect = _upsert

    mock_payer = AsyncMock(spec=PayerAgent)
    from granum.data.denials import Denial, DenialReason
    mock_payer.deny.return_value = Denial(
        denial_id="adv_x", payer="aetna", diagnosis="cardiac",
        cpt_code="93306", icd10_code="I25.10", patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t", submission_date="adversarial",
    )
    mock_judge = AsyncMock(spec=DefensibilityJudge)
    mock_judge.score.return_value = _score(5)

    driver = CoEvolutionDriver(
        phoenix=mock_phoenix,
        payer_agent=mock_payer,
        judge=mock_judge,
        cell="aetna_cardiac",
        gold_path=_GOLD_PATH,
        mutation_proposer=MagicMock(return_value=[]),
    )

    from unittest.mock import patch
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        # Must not raise — retried and succeeded on second payer read.
        outcome = await driver.round()

    assert isinstance(outcome, CoEvolutionRoundResult)
    # Payer prefix was queried at least twice (one empty + one successful).
    assert payer_call_count["n"] >= 2


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
async def test_feedback_directed_writer_mutator_rewrites_strategy_from_critique():
    """When a prompt_mutator is wired, writer clonal expansion rewrites the
    winning STRATEGY from the judge's English critique (directed optimization)
    instead of applying templated citation swaps. The mutator is awaited with
    (winner_body, english_feedback, effective_count), the IMPROVED body is
    upserted (not a templated mutation), and the change note is exposed on
    outcome.writer_mutant_notes."""
    writers = [_writer("w1", "ORIGINAL STRATEGY BODY")]
    payers = [_payer("p1", "strict")]
    # The judge's critique is what the mutator must receive.
    judge_score = _score(8, feedback="cite exact CPB section numbers")

    # Mock feedback-directed mutator: ignores templated mutations entirely and
    # returns a wholesale rewritten strategy + an English change note.
    prompt_mutator = AsyncMock(
        return_value=[("IMPROVED STRATEGY BODY", "tighter citations")]
    )

    # A templated proposer is still supplied (the fallback) but MUST NOT be used
    # when the prompt_mutator is wired.
    templated_proposer = MagicMock(return_value=[])

    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[judge_score],
        mutation_proposer=templated_proposer,
        mutation_count=1,
        prompt_mutator=prompt_mutator,
    )

    outcome = await driver.round()

    # (a) prompt_mutator awaited with winner body + english_feedback + count.
    prompt_mutator.assert_awaited_once()
    call_args = prompt_mutator.await_args.args
    assert call_args[0] == "ORIGINAL STRATEGY BODY"  # winner body
    assert call_args[1] == "cite exact CPB section numbers"  # english_feedback
    assert call_args[2] == 1  # effective mutation count

    # The templated fallback proposer is never consulted with the WRITER body
    # (it may still be called for the payer side). The writer winner body must
    # not appear in any templated-proposer call.
    for call in templated_proposer.call_args_list:
        assert call.kwargs.get("parent") != "ORIGINAL STRATEGY BODY"

    # (b) The IMPROVED body (not a templated mutation) was upserted.
    upsert_calls = mock_phoenix.upsert_prompt.await_args_list
    writer_mutant_upserts = [
        c for c in upsert_calls
        if c.kwargs["name"].startswith("aetna_cardiac/bcell_mut_")
    ]
    assert len(writer_mutant_upserts) == 1
    assert writer_mutant_upserts[0].kwargs["name"] == "aetna_cardiac/bcell_mut_w1_0"
    assert writer_mutant_upserts[0].kwargs["body"] == "IMPROVED STRATEGY BODY"
    assert writer_mutant_upserts[0].kwargs["tags"] == ("experimental",)

    # (c) outcome.writer_mutant_notes carries (prompt_id, note).
    assert len(outcome.writer_mutant_notes) == 1
    mutant_id, note = outcome.writer_mutant_notes[0]
    assert note == "tighter citations"
    assert mutant_id in outcome.writer_mutant_ids


@pytest.mark.asyncio
async def test_feedback_mutator_skips_empty_and_parent_equal_variants():
    """Feedback-directed variants that are empty or identical to the parent are
    skipped — no upsert, no note."""
    writers = [_writer("w1", "PARENT BODY")]
    payers = [_payer("p1", "strict")]
    prompt_mutator = AsyncMock(
        return_value=[
            ("", "empty skipped"),
            ("PARENT BODY", "noop skipped"),
            ("REAL IMPROVEMENT", "kept"),
        ]
    )
    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(8)],
        mutation_count=3,
        prompt_mutator=prompt_mutator,
    )

    outcome = await driver.round()

    writer_mutant_upserts = [
        c for c in mock_phoenix.upsert_prompt.await_args_list
        if c.kwargs["name"].startswith("aetna_cardiac/bcell_mut_")
    ]
    assert len(writer_mutant_upserts) == 1
    assert writer_mutant_upserts[0].kwargs["body"] == "REAL IMPROVEMENT"
    assert [n for _, n in outcome.writer_mutant_notes] == ["kept"]


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


@pytest.mark.asyncio
async def test_round_result_exposes_per_population_scoreboards():
    """writer_scoreboard and payer_scoreboard cover ALL contestants, sorted best-first."""
    writers = [_writer("w1", "winning body w1"), _writer("w2", "losing body w2")]
    payers = [_payer("p1", "strict"), _payer("p2", "lenient")]
    # pair order from tournament cross-product: (w1,p1),(w1,p2),(w2,p1),(w2,p2)
    # defensibility values chosen so:
    #   w1 mean defensibility = (8 + 6) / 2 = 7.0  --> winner
    #   w2 mean defensibility = (4 + 2) / 2 = 3.0  --> loser
    #   p1 inverse mean = ((10-8) + (10-4)) / 2 = (2+6)/2 = 4.0
    #   p2 inverse mean = ((10-6) + (10-2)) / 2 = (4+8)/2 = 6.0 --> p2 wins payer side
    scores = [_score(8), _score(6), _score(4), _score(2)]
    driver, _, _, _ = _make_driver(
        writers=writers, payers=payers, score_side_effect=scores
    )

    outcome = await driver.round()

    # writer_scoreboard: both writers present, sorted by mean defensibility descending
    assert hasattr(outcome, "writer_scoreboard")
    assert len(outcome.writer_scoreboard) == 2
    w_ids = [entry[0] for entry in outcome.writer_scoreboard]
    assert w_ids[0] == "w1"   # winner first
    assert w_ids[1] == "w2"   # loser second
    assert outcome.writer_scoreboard[0][1] == pytest.approx((8 + 6) / 2)  # 7.0
    assert outcome.writer_scoreboard[1][1] == pytest.approx((4 + 2) / 2)  # 3.0

    # payer_scoreboard: both payers present, sorted by mean inverse defensibility descending
    assert hasattr(outcome, "payer_scoreboard")
    assert len(outcome.payer_scoreboard) == 2
    p_ids = [entry[0] for entry in outcome.payer_scoreboard]
    assert p_ids[0] == "p2"   # p2 has higher inverse mean (6.0 > 4.0)
    assert p_ids[1] == "p1"
    assert outcome.payer_scoreboard[0][1] == pytest.approx(((10 - 6) + (10 - 2)) / 2)  # 6.0
    assert outcome.payer_scoreboard[1][1] == pytest.approx(((10 - 8) + (10 - 4)) / 2)  # 4.0


# ---------------------------------------------------------------------------
# Bug 1: _extract_persona_id handles Phoenix-normalized names (__ separator)
# ---------------------------------------------------------------------------

def test_extract_persona_id_slash_baseline() -> None:
    """Original slash-style baseline name still parses."""
    assert _extract_persona_id("aetna_cardiac_payer/baseline_evidence_focused") == "evidence_focused"


def test_extract_persona_id_slash_mutant() -> None:
    """Original slash-style mutant name still parses."""
    assert _extract_persona_id("aetna_cardiac_payer/mut_strict_0") == "strict"


def test_extract_persona_id_double_underscore_baseline() -> None:
    """Phoenix-normalized baseline name (__ instead of /) parses correctly."""
    assert _extract_persona_id("aetna_cardiac_payer__baseline_evidence_focused") == "evidence_focused"


def test_extract_persona_id_double_underscore_mutant() -> None:
    """Phoenix-normalized mutant name (__ instead of /) parses correctly."""
    assert _extract_persona_id("aetna_cardiac_payer__mut_strict_0") == "strict"


def test_extract_persona_id_double_underscore_cost_focused() -> None:
    """Phoenix-normalized name with multi-word persona id parses correctly."""
    assert _extract_persona_id("aetna_cardiac_payer__baseline_cost_focused") == "cost_focused"


def test_extract_persona_id_raises_on_unparseable_name() -> None:
    """A name with neither / nor __ separator raises ValueError."""
    import pytest
    with pytest.raises(ValueError, match="can't parse persona"):
        _extract_persona_id("no_separator_at_all_baseline")


# ---------------------------------------------------------------------------
# Bug 2: dataset writeback is best-effort — failure must NOT abort the round
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_writeback_failure_does_not_abort_round() -> None:
    """If add_dataset_examples raises, round() still returns CoEvolutionRoundResult."""
    writers = [_writer("w1")]
    payers = [_payer("p1", "strict")]
    driver, mock_phoenix, _, _ = _make_driver(
        writers=writers,
        payers=payers,
        score_side_effect=[_score(7)],
    )
    # Simulate the dataset not existing on first live run.
    mock_phoenix.add_dataset_examples.side_effect = RuntimeError(
        "dataset granum/aetna_cardiac/coevolution not found"
    )

    # Must NOT raise — best-effort writeback, round continues.
    outcome = await driver.round()
    assert isinstance(outcome, CoEvolutionRoundResult)
    assert outcome.writer_winner_id == "w1"
    assert outcome.payer_winner_id == "p1"
