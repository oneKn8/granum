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
