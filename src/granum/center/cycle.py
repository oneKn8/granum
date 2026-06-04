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
from typing import Awaitable, Callable, Protocol

from opentelemetry import trace

from granum.center.judge import LLMJudge
from granum.center.mutation import Mutation, apply_mutation
from granum.center.negative_selection import verify_citations
from granum.center.observability import cycle_story_attributes, format_telemetry_digest
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


# Generates an appeal letter from a B-cell system prompt + the denial.
# Optional: when provided, the cycle judges GENERATED appeals (the honest loop);
# when absent, it judges the prompt bodies directly (preserves legacy behavior).
_AppealGenerator = Callable[[str, Denial], Awaitable[str]]

# Feedback-directed mutation: given the winning STRATEGY body + the judge's English
# critique of its appeal, return N improved (body, note) variants. This is directed
# optimization (mutants can actually beat the parent), unlike the mechanical
# citation-swap proposer. When absent, the cycle uses the mechanical proposer.
# Returns: list of (improved_strategy_body, short_change_note).
_PromptMutator = Callable[[str, str, int], Awaitable[list[tuple[str, str]]]]


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
    winner_appeal: str = ""
    english_feedback: str = ""
    scoreboard: tuple[tuple[str, float], ...] = ()
    mutant_notes: tuple[tuple[str, str], ...] = ()
    generation: int = 0


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
        survival_count: int = 1,
        appeal_generator: _AppealGenerator | None = None,
        prompt_mutator: _PromptMutator | None = None,
        read_self_observability: bool = False,
    ) -> None:
        if survival_count < 1:
            raise ValueError(f"survival_count must be >= 1; got {survival_count!r}")
        self._phoenix = phoenix
        self._judge = judge
        self._cell = cell
        self._valid_citations_path = valid_citations_path
        self._gold = load_gold_appeals(gold_path)
        self._propose_mutations = mutation_proposer
        self._mutation_count = mutation_count
        # Elitist top-K selection: the best `survival_count` strategies survive
        # each generation (a germinal center retains many high-affinity clones),
        # not just the single winner. 1 = legacy winner-take-all truncation.
        self._survival_count = survival_count
        self._generate_appeal = appeal_generator
        self._mutate_prompt = prompt_mutator
        # Arize bonus loop: when True, gen>0 reads this cell's own prior-generation
        # telemetry back from Phoenix (get-spans) to inform the mutation.
        self._read_self_observability = read_self_observability

    async def run(
        self,
        *,
        denial: Denial,
        generation: int = 0,
        run_started_at: str | None = None,
    ) -> CycleOutcome:
        with _tracer.start_as_current_span(f"granum.cycle.{self._cell}") as span:
            span.set_attribute("granum.cell", self._cell)
            span.set_attribute("granum.denial_id", denial.denial_id)
            span.set_attribute("granum.generation", generation)

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

            # 2.5 Appeal generation (the honest loop): each surviving B-cell drafts
            # an appeal for THIS denial; the judge then scores the GENERATED appeal,
            # not the strategy text. Falls back to judging the prompt body directly
            # when no generator is wired (keeps the pure-unit path intact).
            prompt_body_by_id = {pv.prompt_id: pv.body for pv in survivors}
            appeal_by_id: dict[str, str] = {}
            if self._generate_appeal is not None:
                with _tracer.start_as_current_span("granum.cycle.appeal_generation"):
                    for pv in survivors:
                        appeal_by_id[pv.prompt_id] = await self._generate_appeal(
                            pv.body, denial
                        )
            else:
                appeal_by_id = dict(prompt_body_by_id)

            # 3. Tournament — judge the generated appeals
            with _tracer.start_as_current_span("granum.cycle.tournament"):
                tournament = Tournament(judge=self._judge, gold=self._gold)
                candidates = [
                    (pv.prompt_id, pv.version_id, appeal_by_id[pv.prompt_id])
                    for pv in survivors
                ]
                tournament_result = await tournament.run(candidates=candidates)

            winner_id, winner_version, winner_appeal = tournament_result.winner
            # Mutation operates on the winning PROMPT, never the generated appeal.
            winner_body = prompt_body_by_id[winner_id]
            winner_feedback = tournament_result.winner_score.english_feedback

            # Elitist top-K survival: rank all scored candidates best-first and
            # keep the top `survival_count`; only the ranked[K:] tail is apoptosed.
            # (survival_count=1 → ranked[1:], the legacy winner-take-all behavior.)
            ranked = sorted(
                tournament_result.all_scores,
                key=lambda s: (-s.score.composite, s.prompt_id),
            )
            culled = ranked[self._survival_count:]

            # 4. Apoptosis losers
            with _tracer.start_as_current_span("granum.cycle.apoptosis"):
                tombstoned_ids: list[str] = [pv.prompt_id for pv in rejected]
                for s in culled:
                    await self._phoenix.tombstone(s.prompt_id, s.version_id)
                    tombstoned_ids.append(s.prompt_id)

            # 5. Promote winner (idempotent — move-semantic tag)
            with _tracer.start_as_current_span("granum.cycle.promote"):
                await self._phoenix.add_version_tag(
                    winner_id, winner_version, "production"
                )

            # 5.5 Self-improvement observability loop (Arize bonus). Before
            # mutating, read this cell's OWN prior-generation telemetry back from
            # Phoenix (get-spans) and let the mutator optimize against the
            # weaknesses its observability data reveals across generations.
            # Best-effort: a cold/failed read falls back to this generation's
            # in-memory critique, so the loop never breaks the run.
            mutator_feedback = winner_feedback
            if (
                self._read_self_observability
                and generation > 0
                and self._mutate_prompt is not None
            ):
                with _tracer.start_as_current_span(
                    "granum.cycle.read_self_observability"
                ) as obs_span:
                    history = await self._phoenix.read_self_improvement_history(
                        cell=self._cell, since=run_started_at
                    )
                    digest = format_telemetry_digest(history)
                    obs_span.set_attribute(
                        "granum.observability_readback_generations", len(history)
                    )
                    if digest:
                        mutator_feedback = (
                            f"{digest}\n\n## This generation's evaluation\n"
                            f"{winner_feedback}"
                        )

            # 6. Clonal expansion — winning lineage proliferates into mutated
            # daughters. Mutants are tagged `production` (NOT experimental): in a
            # germinal center the daughters are active members that compete in the
            # NEXT round of selection, not benched. Generation-scoped names keep
            # them unique + traceable across a multi-generation run.
            with _tracer.start_as_current_span("granum.cycle.clonal_expansion"):
                mutant_ids: list[str] = []
                mutant_notes: list[tuple[str, str]] = []
                # Each (improved_body, note) candidate daughter.
                proposals: list[tuple[str, str]] = []
                if self._mutate_prompt is not None:
                    # Feedback-directed: rewrite the winning strategy to address the
                    # judge's critique. Directed optimization — daughters can beat
                    # the parent, so the champion genuinely evolves.
                    proposals = await self._mutate_prompt(
                        winner_body, mutator_feedback, self._mutation_count
                    )
                else:
                    # Mechanical fallback (citation swaps / reframes). Seeded by
                    # generation for reproducibility; no-ops are skipped below.
                    for mutation in self._propose_mutations(
                        parent=winner_body, n=self._mutation_count, seed=generation
                    ):
                        try:
                            body = apply_mutation(winner_body, mutation)
                        except ValueError as e:
                            _log.warning("mutation on winner %s failed: %s", winner_id, e)
                            continue
                        note = (
                            f"{mutation.kind.value}: "
                            f"{mutation.target} → {mutation.replacement}"
                        )
                        proposals.append((body, note))

                for i, (mutant_body, note) in enumerate(proposals):
                    if not mutant_body or mutant_body == winner_body:
                        continue  # empty or no-op daughter
                    name = f"{self._cell}/g{generation + 1}m{i}"
                    pv = await self._phoenix.upsert_prompt(
                        name=name, body=mutant_body, tags=("production",)
                    )
                    mutant_ids.append(pv.prompt_id)
                    mutant_notes.append((pv.prompt_id, note))

            # Rich span attributes: make the Phoenix trace tell the self-improvement
            # story (winner, fitness, apoptosis, mutations, the judge's critique) so
            # a judge reading the trace sees the climb — and so the NEXT generation
            # can read this telemetry back (the bonus loop in step 5.5).
            for _key, _val in cycle_story_attributes(
                cell=self._cell,
                generation=generation,
                winner_id=winner_id,
                winner_fitness=tournament_result.winner_score.composite,
                population_size=len(ranked) - len(culled),
                apoptosis_ids=tuple(tombstoned_ids),
                mutant_notes=tuple(mutant_notes),
                rejected_count=len(rejected),
                critique=winner_feedback,
            ).items():
                span.set_attribute(_key, _val)

            # 7. Dataset writeback (best-effort — Phoenix MCP has no create-dataset,
            # so the outcomes dataset may not exist on a first live run. A missing
            # dataset must NOT abort the evolution core, which is already committed
            # to Phoenix via the prompt-version tags above.)
            with _tracer.start_as_current_span("granum.cycle.dataset_writeback") as ws:
                try:
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
                except Exception as exc:  # noqa: BLE001 — writeback is supplementary
                    ws.set_attribute("granum.dataset_writeback.ok", False)
                    _log.warning(
                        "dataset writeback to granum/%s/outcomes failed (dataset may "
                        "not exist yet): %s", self._cell, exc,
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
                winner_appeal=winner_appeal,
                english_feedback=tournament_result.winner_score.english_feedback,
                scoreboard=tuple(
                    (s.prompt_id, s.score.composite)
                    for s in tournament_result.all_scores
                ),
                mutant_notes=tuple(mutant_notes),
                generation=generation,
            )
