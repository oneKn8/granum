"""Co-evolution driver — one Red Queen round per cell.

Pipeline (mirrors GerminalCycle but dual-population):
1. Load active writer population (Phoenix name prefix `{cell}/`).
2. Load active payer population (Phoenix name prefix `{cell}_payer/`).
3. Triangular tournament: writers x payers cross product scored by
   DefensibilityJudge via PayerAgent.
4. Apoptosis losers in BOTH populations (tombstone via Phoenix client).
5. Promote winners in BOTH populations (production tag on each).
6. Clonal expansion: propose K mutations on writer winner, K on payer
   winner, upsert each as new experimental prompts.
7. Dataset writeback to `granum/{cell}/coevolution`.

OTel spans bracket each phase for Phoenix trace introspection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from opentelemetry import trace

from granum.adversary.payer_agent import PayerAgent
from granum.adversary.payer_persona import SEEDED_PERSONAS
from granum.center.defensibility_judge import DefensibilityJudge
from granum.center.mutation import Mutation, apply_mutation
from granum.center.triangular_tournament import (
    PayerRef,
    TriangularTournament,
    WriterRef,
)
from granum.data.gold import load_gold_appeals
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


_log = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


class _MutationProposer(Protocol):
    def __call__(
        self, *, parent: str, n: int, seed: int | None = None
    ) -> list[Mutation]: ...


@dataclass(frozen=True)
class CoEvolutionRoundResult:
    cell: str
    round_index: int
    writer_winner_id: str
    payer_winner_id: str
    writer_loser_ids: tuple[str, ...]
    payer_loser_ids: tuple[str, ...]
    writer_mutant_ids: tuple[str, ...]
    payer_mutant_ids: tuple[str, ...]
    defensibility_composite: float
    english_feedback: str
    adversary_reset_fired: bool = False


def _extract_persona_id(prompt_name: str) -> str:
    """Parse persona_id from a payer-prompt name.

    Convention:
        {cell}_payer/baseline_<persona_id>
        {cell}_payer/mut_<persona_id>_<index>
    """
    if "/" not in prompt_name:
        raise ValueError(f"can't parse persona from {prompt_name!r}")
    suffix = prompt_name.rsplit("/", 1)[1]
    if suffix.startswith("baseline_"):
        return suffix[len("baseline_"):]
    if suffix.startswith("mut_"):
        # mut_<persona_id>_<index> — strip leading "mut_" and trailing "_<index>"
        rest = suffix[len("mut_"):]
        if "_" not in rest:
            raise ValueError(f"can't parse persona from {prompt_name!r}")
        return rest.rsplit("_", 1)[0]
    raise ValueError(f"can't parse persona from {prompt_name!r}")


class CoEvolutionDriver:
    def __init__(
        self,
        *,
        phoenix: PhoenixClient,
        payer_agent: PayerAgent,
        judge: DefensibilityJudge,
        cell: str,
        gold_path: str | Path,
        mutation_proposer: _MutationProposer,
        mutation_count: int = 2,
        mutation_rate_cap: float = 0.15,
        adversary_reset_every: int = 5,
    ) -> None:
        if not (0.0 <= mutation_rate_cap <= 1.0):
            raise ValueError(
                f"mutation_rate_cap must be in [0.0, 1.0]; got {mutation_rate_cap!r}"
            )
        if adversary_reset_every < 1:
            raise ValueError(
                f"adversary_reset_every must be >= 1; got {adversary_reset_every!r}"
            )
        self._phoenix = phoenix
        self._payer_agent = payer_agent
        self._judge = judge
        self._cell = cell
        self._gold = load_gold_appeals(gold_path)
        self._propose_mutations = mutation_proposer
        self._mutation_count = mutation_count
        self._mutation_rate_cap = mutation_rate_cap
        self._adversary_reset_every = adversary_reset_every
        self._round_index = 0

    def _effective_mutation_count(self, population_size: int) -> int:
        cap = max(1, int(population_size * self._mutation_rate_cap))
        return min(self._mutation_count, cap)

    async def round(self) -> CoEvolutionRoundResult:
        with _tracer.start_as_current_span("granum.coevolution.round") as span:
            span.set_attribute("granum.cell", self._cell)
            span.set_attribute("granum.round_index", self._round_index)

            # 1. Load active writer population
            with _tracer.start_as_current_span("granum.coevolution.load_writers"):
                writers = await self._phoenix.list_active_prompts(
                    name_prefix=f"{self._cell}/"
                )
            if not writers:
                raise RuntimeError(
                    f"co-evolution cell {self._cell} has empty writer population"
                )

            # 2. Load active payer population
            with _tracer.start_as_current_span("granum.coevolution.load_payers"):
                payers = await self._phoenix.list_active_prompts(
                    name_prefix=f"{self._cell}_payer/"
                )
            if not payers:
                raise RuntimeError(
                    f"co-evolution cell {self._cell} has empty payer population"
                )

            writer_refs: list[WriterRef] = [
                (pv.prompt_id, pv.version_id, pv.body) for pv in writers
            ]
            payer_refs: list[PayerRef] = [
                (pv.prompt_id, pv.version_id, _extract_persona_id(pv.name))
                for pv in payers
            ]
            # Map prompt_id -> source PromptVersion for body lookup post-tournament
            payer_by_id: dict[str, PromptVersion] = {
                pv.prompt_id: pv for pv in payers
            }

            # 3. Triangular tournament
            with _tracer.start_as_current_span("granum.coevolution.tournament"):
                tournament = TriangularTournament(
                    payer_agent=self._payer_agent,
                    judge=self._judge,
                    gold=self._gold,
                )
                result = await tournament.run(
                    writer_candidates=writer_refs,
                    payer_candidates=payer_refs,
                )

            writer_winner_id, writer_winner_version, writer_winner_body = (
                result.writer_winner
            )
            payer_winner_id, payer_winner_version, payer_winner_persona = (
                result.payer_winner
            )

            # 4. Apoptosis losers — BOTH populations
            with _tracer.start_as_current_span("granum.coevolution.apoptosis"):
                writer_loser_ids: list[str] = []
                for loser_id, loser_version, _ in result.writer_losers:
                    await self._phoenix.tombstone(loser_id, loser_version)
                    writer_loser_ids.append(loser_id)
                payer_loser_ids: list[str] = []
                for loser_id, loser_version, _ in result.payer_losers:
                    await self._phoenix.tombstone(loser_id, loser_version)
                    payer_loser_ids.append(loser_id)

            # 5. Promote winners — BOTH populations
            with _tracer.start_as_current_span("granum.coevolution.promote"):
                await self._phoenix.add_version_tag(
                    writer_winner_id, writer_winner_version, "production"
                )
                await self._phoenix.add_version_tag(
                    payer_winner_id, payer_winner_version, "production"
                )

            # 6. Clonal expansion — writer winner
            writer_effective_count = self._effective_mutation_count(
                len(writer_refs)
            )
            with _tracer.start_as_current_span(
                "granum.coevolution.clonal_expansion_writers"
            ):
                writer_mutant_ids: list[str] = []
                writer_mutations = self._propose_mutations(
                    parent=writer_winner_body, n=writer_effective_count
                )
                for i, mutation in enumerate(writer_mutations):
                    try:
                        mutant_body = apply_mutation(writer_winner_body, mutation)
                    except ValueError as e:
                        _log.warning(
                            "writer mutation %d on winner %s failed: %s — skipping",
                            i, writer_winner_id, e,
                        )
                        continue
                    if mutant_body == writer_winner_body:
                        continue
                    name = f"{self._cell}/bcell_mut_{writer_winner_id}_{i}"
                    pv = await self._phoenix.upsert_prompt(
                        name=name, body=mutant_body, tags=("experimental",)
                    )
                    writer_mutant_ids.append(pv.prompt_id)

            # 6b. Clonal expansion — payer winner
            payer_effective_count = self._effective_mutation_count(
                len(payer_refs)
            )
            with _tracer.start_as_current_span(
                "granum.coevolution.clonal_expansion_payers"
            ):
                payer_mutant_ids: list[str] = []
                payer_mutant_versions: list[tuple[str, str]] = []
                payer_winner_body = payer_by_id[payer_winner_id].body
                payer_mutations = self._propose_mutations(
                    parent=payer_winner_body, n=payer_effective_count
                )
                for i, mutation in enumerate(payer_mutations):
                    try:
                        mutant_body = apply_mutation(payer_winner_body, mutation)
                    except ValueError as e:
                        _log.warning(
                            "payer mutation %d on winner %s failed: %s — skipping",
                            i, payer_winner_id, e,
                        )
                        continue
                    if mutant_body == payer_winner_body:
                        continue
                    name = (
                        f"{self._cell}_payer/mut_{payer_winner_persona}_{i}"
                    )
                    pv = await self._phoenix.upsert_prompt(
                        name=name, body=mutant_body, tags=("experimental",)
                    )
                    payer_mutant_ids.append(pv.prompt_id)
                    payer_mutant_versions.append((pv.prompt_id, pv.version_id))

            # Compute winner's mean defensibility composite across all the
            # payers it faced — the judge produces per-pair composite scores;
            # we average the composites of the writer-winner's pair scores.
            winner_pair_scores = [
                ps for ps in result.all_pair_scores
                if ps.writer_id == writer_winner_id
            ]
            if winner_pair_scores:
                composite = sum(
                    ps.score.composite for ps in winner_pair_scores
                ) / len(winner_pair_scores)
                english_feedback = winner_pair_scores[0].score.english_feedback
            else:  # pragma: no cover — defensive
                composite = 0.0
                english_feedback = ""

            # 7. Dataset writeback
            with _tracer.start_as_current_span(
                "granum.coevolution.dataset_writeback"
            ):
                await self._phoenix.add_dataset_examples(
                    dataset_name=f"granum/{self._cell}/coevolution",
                    examples=[{
                        "round_index": self._round_index,
                        "writer_winner_id": writer_winner_id,
                        "payer_winner_id": payer_winner_id,
                        "defensibility_composite": composite,
                        "english_feedback": english_feedback,
                        "writer_loser_count": len(writer_loser_ids),
                        "payer_loser_count": len(payer_loser_ids),
                    }],
                )

            # 8. Adversary reset check — fires when (round_index + 1) is a
            # multiple of adversary_reset_every. Wipes the FULL current payer
            # population (active payers + just-spawned mutants, dedup'd
            # against tournament-loser tombstones) and re-seeds from
            # SEEDED_PERSONAS.
            adversary_reset_fired = (
                (self._round_index + 1) % self._adversary_reset_every == 0
            )
            if adversary_reset_fired:
                with _tracer.start_as_current_span(
                    "granum.coevolution.adversary_reset"
                ):
                    # Collect every payer (id, version) pair currently active
                    # after this round's mutations: the original payers plus
                    # the just-upserted mutants. Dedup against losers already
                    # tombstoned in step 4.
                    already_tombstoned = {
                        (lid, lver)
                        for lid, lver, _ in result.payer_losers
                    }
                    full_payer_pop: list[tuple[str, str]] = []
                    for pv in payers:
                        full_payer_pop.append((pv.prompt_id, pv.version_id))
                    # Just-spawned payer mutants from this round's clonal
                    # expansion — captured during step 6b.
                    for pid, ver in payer_mutant_versions:
                        full_payer_pop.append((pid, ver))
                    seen: set[tuple[str, str]] = set()
                    for pid, ver in full_payer_pop:
                        if (pid, ver) in already_tombstoned:
                            continue
                        if (pid, ver) in seen:
                            continue
                        seen.add((pid, ver))
                        await self._phoenix.tombstone(pid, ver)
                    # Re-seed from baseline personas.
                    for persona in SEEDED_PERSONAS:
                        await self._phoenix.upsert_prompt(
                            name=(
                                f"{self._cell}_payer/"
                                f"baseline_{persona.persona_id}"
                            ),
                            body=persona.system_prompt,
                            tags=("experimental",),
                        )

            outcome = CoEvolutionRoundResult(
                cell=self._cell,
                round_index=self._round_index,
                writer_winner_id=writer_winner_id,
                payer_winner_id=payer_winner_id,
                writer_loser_ids=tuple(writer_loser_ids),
                payer_loser_ids=tuple(payer_loser_ids),
                writer_mutant_ids=tuple(writer_mutant_ids),
                payer_mutant_ids=tuple(payer_mutant_ids),
                defensibility_composite=composite,
                english_feedback=english_feedback,
                adversary_reset_fired=adversary_reset_fired,
            )
            self._round_index += 1
            return outcome
