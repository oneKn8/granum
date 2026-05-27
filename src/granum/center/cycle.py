"""Germinal cycle — one full evolution round for a single (payer × diagnosis) cell.

Pipeline:
1. list active prompts from Phoenix (production tag, not tombstoned)
2. negative selection — reject hallucinated citations, missing deadlines
3. tournament — concurrent LLM-as-judge across survivors vs gold dataset
4. tombstone losers (functional apoptosis, Path B)
5. promote winner → 'production' tag (move-semantic, demotes prior champion)
6. clonal expansion — propose K small mutations on winner, upsert each as
   new experimental prompt
7. dataset writeback — record outcome (winner id, composite score, English feedback)

OTel spans bracket each phase for Phoenix trace introspection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from opentelemetry import trace

from granum.center.judge import LLMJudge
from granum.center.mutation import Mutation, apply_mutation
from granum.center.negative_selection import verify_citations
from granum.center.tournament import Tournament
from granum.data.denials import Denial
from granum.data.gold import load_gold_appeals
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


_log = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


class _MutationProposer(Protocol):
    def __call__(
        self, *, parent: str, n: int, seed: int | None = None
    ) -> list[Mutation]: ...


@dataclass(frozen=True)
class CycleOutcome:
    cell: str
    denial_id: str
    survivors_before_tournament: tuple[str, ...]
    rejected_by_negative_selection: tuple[str, ...]
    winner_id: str
    winner_version_id: str
    winner_composite_score: float
    tombstoned_ids: tuple[str, ...]
    mutant_ids: tuple[str, ...]


class GerminalCycle:
    def __init__(
        self,
        *,
        phoenix: PhoenixClient,
        judge: LLMJudge,
        cell: str,
        valid_citations_path: str | Path,
        gold_path: str | Path,
        mutation_proposer: _MutationProposer,
        mutation_count: int = 2,
    ) -> None:
        self._phoenix = phoenix
        self._judge = judge
        self._cell = cell
        self._valid_citations_path = valid_citations_path
        self._gold = load_gold_appeals(gold_path)
        self._propose_mutations = mutation_proposer
        self._mutation_count = mutation_count

    async def run(self, *, denial: Denial) -> CycleOutcome:
        with _tracer.start_as_current_span(f"granum.cycle.{self._cell}") as span:
            span.set_attribute("granum.cell", self._cell)
            span.set_attribute("granum.denial_id", denial.denial_id)

            # 1. Load active population
            with _tracer.start_as_current_span("granum.cycle.load_active"):
                active = await self._phoenix.list_active_prompts(
                    name_prefix=f"{self._cell}/"
                )

            # 2. Negative selection
            with _tracer.start_as_current_span("granum.cycle.negative_selection"):
                survivors: list[PromptVersion] = []
                rejected: list[PromptVersion] = []
                for pv in active:
                    result = verify_citations(
                        pv.body, valid_set_path=self._valid_citations_path
                    )
                    if result.passed:
                        survivors.append(pv)
                    else:
                        _log.info(
                            "negative_selection rejecting %s/%s — %s",
                            pv.prompt_id, pv.version_id, result.reasons,
                        )
                        rejected.append(pv)
                        await self._phoenix.tombstone(pv.prompt_id, pv.version_id)

            if not survivors:
                raise RuntimeError(
                    f"No survivors after negative selection in cell {self._cell}"
                )

            # 3. Tournament
            with _tracer.start_as_current_span("granum.cycle.tournament"):
                tournament = Tournament(judge=self._judge, gold=self._gold)
                candidates = [
                    (pv.prompt_id, pv.version_id, pv.body) for pv in survivors
                ]
                tournament_result = await tournament.run(candidates=candidates)

            winner_id, winner_version, winner_body = tournament_result.winner

            # 4. Apoptosis losers
            with _tracer.start_as_current_span("granum.cycle.apoptosis"):
                tombstoned_ids: list[str] = [pv.prompt_id for pv in rejected]
                for loser_id, loser_version, _ in tournament_result.losers:
                    await self._phoenix.tombstone(loser_id, loser_version)
                    tombstoned_ids.append(loser_id)

            # 5. Promote winner (idempotent — move-semantic tag)
            with _tracer.start_as_current_span("granum.cycle.promote"):
                await self._phoenix.add_version_tag(
                    winner_id, winner_version, "production"
                )

            # 6. Clonal expansion
            with _tracer.start_as_current_span("granum.cycle.clonal_expansion"):
                mutant_ids: list[str] = []
                mutations = self._propose_mutations(
                    parent=winner_body, n=self._mutation_count
                )
                for i, mutation in enumerate(mutations):
                    try:
                        mutant_body = apply_mutation(winner_body, mutation)
                    except ValueError as e:
                        _log.warning(
                            "mutation %d on winner %s failed: %s — skipping",
                            i, winner_id, e,
                        )
                        continue
                    if mutant_body == winner_body:
                        # No-op mutation; skip
                        continue
                    name = f"{self._cell}/bcell_mut_{winner_id}_{i}"
                    pv = await self._phoenix.upsert_prompt(
                        name=name, body=mutant_body, tags=("experimental",)
                    )
                    mutant_ids.append(pv.prompt_id)

            # 7. Dataset writeback
            with _tracer.start_as_current_span("granum.cycle.dataset_writeback"):
                await self._phoenix.add_dataset_examples(
                    dataset_name=f"granum/{self._cell}/outcomes",
                    examples=[{
                        "denial_id": denial.denial_id,
                        "winner_prompt_id": winner_id,
                        "winner_version_id": winner_version,
                        "winner_composite": tournament_result.winner_score.composite,
                        "rejected_count": len(rejected),
                        "loser_count": len(tournament_result.losers),
                        "mutant_count": len(mutant_ids),
                        "english_feedback": tournament_result.winner_score.english_feedback,
                    }],
                )

            return CycleOutcome(
                cell=self._cell,
                denial_id=denial.denial_id,
                survivors_before_tournament=tuple(
                    pv.prompt_id for pv in survivors
                ),
                rejected_by_negative_selection=tuple(
                    pv.prompt_id for pv in rejected
                ),
                winner_id=winner_id,
                winner_version_id=winner_version,
                winner_composite_score=tournament_result.winner_score.composite,
                tombstoned_ids=tuple(tombstoned_ids),
                mutant_ids=tuple(mutant_ids),
            )
