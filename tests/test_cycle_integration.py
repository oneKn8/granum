"""Integration test — one full germinal-center cycle.

All Phoenix MCP + REST calls mocked. Verifies the orchestration glues
together correctly: load active → negative-select → tournament → tombstone
losers → mutate winner → writeback dataset → emit OTel spans.
"""
import pytest
from unittest.mock import AsyncMock

from granum.center.cycle import GerminalCycle, CycleOutcome
from granum.center.judge import JudgeScore
from granum.center.mutation import Mutation, MutationKind
from granum.data.denials import generate_denial
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_full_cycle_negative_selects_then_tournaments_then_tombstones():
    """End-to-end one cycle:
    - 3 B-cells active (bc1, bc2, bc3)
    - bc3 has hallucinated CPB → negative selection tombstones it
    - bc1 vs bc2 tournament → bc1 wins (higher composite)
    - bc2 tombstoned, bc1 promoted to production
    - 2 mutations spawned from bc1 (mock proposer returns 2 mutations)
    - Outcome written to dataset
    """
    phoenix = AsyncMock(spec=PhoenixClient)
    # list_active_prompts returns 3 production B-cells
    phoenix.list_active_prompts.return_value = [
        PromptVersion(
            prompt_id="bc1",
            version_id="v1",
            tags=("production",),
            body="Per Aetna CPB 0119 §IV.A we appeal. ACC/AHA 2021 §6.2 supports. Per 29 CFR 2560.503-1 we request reconsideration within 30 days.",
        ),
        PromptVersion(
            prompt_id="bc2",
            version_id="v1",
            tags=("production",),
            body="Per Aetna CPB 0286 §III we appeal. ACC/AHA 2020 Heart Failure applies. Appeal deadline: 30 days.",
        ),
        PromptVersion(
            prompt_id="bc3",
            version_id="v1",
            tags=("production",),
            body="Per Aetna CPB 9999 we appeal. Appeal deadline: 30 days.",  # hallucinated CPB
        ),
    ]
    # tombstone is a no-op (mocked)
    phoenix.tombstone.return_value = None
    # upsert_prompt returns new versions for the 2 mutants
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id="bc1m1", version_id="v1", tags=("experimental",), body="mut1"),
        PromptVersion(prompt_id="bc1m2", version_id="v1", tags=("experimental",), body="mut2"),
    ]
    # add_version_tag for the champion promotion
    phoenix.add_version_tag.return_value = ("production",)
    # add_dataset_examples no-op
    phoenix.add_dataset_examples.return_value = None

    # Mock judge: bc1 scores 8.0 (wins), bc2 scores 6.0 (loses)
    judge = AsyncMock()
    judge.score.side_effect = [
        JudgeScore(8, 8, 8, 8, 8, "bc1 best"),
        JudgeScore(6, 6, 6, 6, 6, "bc2 weaker"),
    ]

    # Mock mutation proposer
    def fake_proposer(*, parent, n, seed=None):
        return [
            Mutation(
                kind=MutationKind.CITATION_SWAP,
                target="Aetna CPB 0119",
                replacement="Aetna CPB 0286",
            ),
            Mutation(
                kind=MutationKind.PARAGRAPH_REFRAME,
                target="we appeal",
                replacement="we respectfully appeal",
            ),
        ]

    cycle = GerminalCycle(
        phoenix=phoenix,
        judge=judge,
        cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=fake_proposer,
        mutation_count=2,
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    outcome = await cycle.run(denial=denial)

    assert isinstance(outcome, CycleOutcome)
    # Negative selection caught bc3
    assert "bc3" in outcome.rejected_by_negative_selection
    # Tournament chose bc1
    assert outcome.winner_id == "bc1"
    # bc2 tombstoned (lost tournament), bc3 also tombstoned (NS failure)
    assert "bc2" in outcome.tombstoned_ids
    assert "bc3" in outcome.tombstoned_ids
    # Two mutants spawned
    assert len(outcome.mutant_ids) == 2

    # Phoenix calls happened
    assert phoenix.list_active_prompts.called
    assert phoenix.tombstone.call_count == 2  # bc3 + bc2
    assert phoenix.upsert_prompt.call_count == 2  # 2 mutants
    assert phoenix.add_version_tag.called  # champion promotion
    assert phoenix.add_dataset_examples.called  # writeback


@pytest.mark.asyncio
async def test_cycle_uses_feedback_directed_mutator_when_provided():
    """When a prompt_mutator is wired, daughters come from it (fed the judge's
    critique), NOT the mechanical proposer."""
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(
            prompt_id="bc1",
            version_id="v1",
            tags=("production",),
            body="Per Aetna CPB 0119 §IV.A we appeal. ACC/AHA 2021 §6.2 supports. Per 29 CFR 2560.503-1 we request reconsideration within 30 days.",
        ),
    ]
    phoenix.tombstone.return_value = None
    phoenix.add_version_tag.return_value = ("production",)
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id="g1m0", version_id="v1", tags=("production",), body="improved 1"),
        PromptVersion(prompt_id="g1m1", version_id="v1", tags=("production",), body="improved 2"),
    ]

    judge = AsyncMock()
    judge.score.return_value = JudgeScore(8, 8, 8, 8, 8, "needs sharper section-level citations")

    async def gen_appeal(body, denial):
        return "appeal letter generated from " + body[:10]

    # Mechanical proposer must NOT be used when a prompt_mutator is present.
    mechanical = lambda **kw: (_ for _ in ()).throw(AssertionError("mechanical used"))  # noqa: E731
    mutator = AsyncMock(
        return_value=[("improved 1", "sharper citations"), ("improved 2", "more evidence")]
    )

    cycle = GerminalCycle(
        phoenix=phoenix,
        judge=judge,
        cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=mechanical,
        mutation_count=2,
        appeal_generator=gen_appeal,
        prompt_mutator=mutator,
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    outcome = await cycle.run(denial=denial, generation=0)

    # mutator received the winner's body + the judge's feedback + the count
    mutator.assert_awaited_once()
    args = mutator.await_args[0]
    assert args[1] == "needs sharper section-level citations"
    assert args[2] == 2
    # 2 daughters spawned from the mutator output, with its notes
    assert len(outcome.mutant_ids) == 2
    assert phoenix.upsert_prompt.await_count == 2
    notes = dict(outcome.mutant_notes)
    assert notes["g1m0"] == "sharper citations"


@pytest.mark.asyncio
async def test_top_k_elitist_survival_keeps_best_k_alive():
    """Algorithm improvement: with survival_count=K the top-K candidates survive
    (elitist clonal selection) instead of winner-take-all. Only the ranked[K:]
    tail undergoes apoptosis — a near-best strategy is no longer killed for
    placing 2nd, preserving lineage diversity."""
    valid = (
        "Per Aetna CPB 0119 §IV.A we appeal. ACC/AHA 2021 §6.2 supports. "
        "Per 29 CFR 2560.503-1 we request reconsideration within 30 days."
    )
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id=f"bc{i}", version_id="v1", tags=("production",), body=valid)
        for i in range(1, 5)  # bc1..bc4, all pass negative selection
    ]
    phoenix.tombstone.return_value = None
    phoenix.add_version_tag.return_value = ("production",)
    phoenix.add_dataset_examples.return_value = None

    judge = AsyncMock()
    # scored in candidate order bc1..bc4 → composites 9,7,5,3
    judge.score.side_effect = [
        JudgeScore(9, 9, 9, 9, 9, "bc1"),
        JudgeScore(7, 7, 7, 7, 7, "bc2"),
        JudgeScore(5, 5, 5, 5, 5, "bc3"),
        JudgeScore(3, 3, 3, 3, 3, "bc4"),
    ]

    cycle = GerminalCycle(
        phoenix=phoenix,
        judge=judge,
        cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=lambda **kw: [],
        mutation_count=0,
        survival_count=2,
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    outcome = await cycle.run(denial=denial)

    # Winner is still the top strategy.
    assert outcome.winner_id == "bc1"
    # Top-2 survive (NOT tombstoned); bottom-2 culled.
    assert "bc1" not in outcome.tombstoned_ids
    assert "bc2" not in outcome.tombstoned_ids
    assert "bc3" in outcome.tombstoned_ids
    assert "bc4" in outcome.tombstoned_ids
    # Exactly the ranked[K:] tail is apoptosed (no rejected this run).
    assert phoenix.tombstone.await_count == 2


@pytest.mark.asyncio
async def test_self_observability_augments_mutator_feedback_at_gen_gt_0():
    """Arize bonus loop: at gen>0 the cycle reads its own prior-generation
    telemetry back from Phoenix and feeds the distilled digest into the mutator,
    so the mutation is driven by the agent's observability data — not just the
    last in-memory score."""
    from granum.center.observability import GenerationObservation

    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(
            prompt_id="bc1", version_id="v1", tags=("production",),
            body="Per Aetna CPB 0119 §IV.A we appeal. ACC/AHA 2021 §6.2. Per 29 CFR 2560.503-1 within 30 days.",
        ),
    ]
    phoenix.tombstone.return_value = None
    phoenix.add_version_tag.return_value = ("production",)
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id="g2m0", version_id="v1", tags=("production",), body="improved"),
    ]
    # The agent's own telemetry, read back from Phoenix.
    phoenix.read_self_improvement_history.return_value = [
        GenerationObservation(generation=0, winner_fitness=4.0, critique="lacks section-level citations"),
    ]

    judge = AsyncMock()
    judge.score.return_value = JudgeScore(7, 7, 7, 7, 7, "this gen: weak on procedure")

    async def gen_appeal(body, denial):
        return "appeal " + body[:10]

    mutator = AsyncMock(return_value=[("improved", "tighter citations")])

    cycle = GerminalCycle(
        phoenix=phoenix, judge=judge, cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=lambda **kw: [], mutation_count=1,
        appeal_generator=gen_appeal, prompt_mutator=mutator,
        read_self_observability=True,
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    await cycle.run(denial=denial, generation=1)

    # The agent read its own telemetry back...
    phoenix.read_self_improvement_history.assert_awaited_once()
    # ...and the mutator's feedback contains the Phoenix-sourced digest AND this
    # generation's critique.
    feedback_arg = mutator.await_args[0][1]
    assert "lacks section-level citations" in feedback_arg  # from prior-gen telemetry
    assert "Phoenix telemetry" in feedback_arg
    assert "this gen: weak on procedure" in feedback_arg  # current eval still included


@pytest.mark.asyncio
async def test_self_observability_skipped_at_gen_0():
    """Gen 0 has no prior telemetry — no read-back attempted."""
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(
            prompt_id="bc1", version_id="v1", tags=("production",),
            body="Per Aetna CPB 0119 we appeal within 30 days. Per 29 CFR 2560.503-1.",
        ),
    ]
    phoenix.tombstone.return_value = None
    phoenix.add_version_tag.return_value = ("production",)
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id="g1m0", version_id="v1", tags=("production",), body="x"),
    ]
    judge = AsyncMock()
    judge.score.return_value = JudgeScore(6, 6, 6, 6, 6, "fb")

    async def gen_appeal(body, denial):
        return "appeal"

    cycle = GerminalCycle(
        phoenix=phoenix, judge=judge, cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=lambda **kw: [], mutation_count=1,
        appeal_generator=gen_appeal, prompt_mutator=AsyncMock(return_value=[]),
        read_self_observability=True,
    )
    await cycle.run(denial=generate_denial(payer="aetna", diagnosis="cardiac", seed=1), generation=0)
    phoenix.read_self_improvement_history.assert_not_called()


@pytest.mark.asyncio
async def test_cycle_raises_when_all_fail_negative_selection():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(
            prompt_id="bc1",
            version_id="v1",
            tags=("production",),
            body="Per Aetna CPB 9999 we appeal.",  # hallucinated, no deadline
        ),
    ]
    phoenix.tombstone.return_value = None
    judge = AsyncMock()
    cycle = GerminalCycle(
        phoenix=phoenix,
        judge=judge,
        cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
        mutation_proposer=lambda **kw: [],
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)
    with pytest.raises(RuntimeError, match="No survivors after negative selection"):
        await cycle.run(denial=denial)
