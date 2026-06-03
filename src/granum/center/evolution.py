"""Generational evolution — drive the germinal cycle across many generations.

Phase B (1.11): one `GerminalCycle.run` is a single generation. This runner
chains G generations against a consistent antigen (the same denial — the
population affinity-matures to it), accumulating:

  - the lineage tree (each strategy: generation, parent, fitness, final status),
  - per-generation tournament rounds, and
  - a fitness curve (mean/max judge composite per generation).

After the run it sweeps Phoenix once for every strategy's body + final tag, so
the emitted artifact is self-contained (the API can serve it statically without
a live Phoenix/MCP dependency at request time).

`to_payload()` returns the camelCase `CellPayload` shape from
`docs/api-contract.md` — the same JSON the Next.js frontend consumes.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from statistics import mean

from granum.center.cycle import CycleOutcome, GerminalCycle
from granum.data.denials import Denial
from granum.tools.phoenix_client import (
    PhoenixClient,
    PhoenixToolError,
    _extract_template_text,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationRecord:
    generation: int
    denial_id: str
    candidate_ids: tuple[str, ...]
    winner_id: str
    winner_composite: float
    loser_ids: tuple[str, ...]
    scoreboard: tuple[tuple[str, float], ...]
    mutant_ids: tuple[str, ...]
    mutant_notes: tuple[tuple[str, str], ...]
    winner_appeal: str
    english_feedback: str


@dataclass
class _StrategyAccum:
    """Mutable lineage-node accumulator built up across generations."""

    id: str
    generation: int
    parent_id: str | None
    mutation_note: str | None
    fitness: float = 0.0  # last composite it scored (0-10), normalized later
    body: str = ""
    status: str = "active"  # production | tombstoned | active
    tag: str = "production"


@dataclass(frozen=True)
class EvolutionResult:
    cell: str
    generations: tuple[GenerationRecord, ...]
    strategies: tuple[_StrategyAccum, ...]

    def fitness_curve(self) -> list[dict]:
        points: list[dict] = []
        for rec in self.generations:
            comps = [c for _, c in rec.scoreboard]
            points.append(
                {
                    "generation": rec.generation,
                    "meanFitness": round(mean(comps) / 10.0, 4) if comps else 0.0,
                    "maxFitness": round(max(comps) / 10.0, 4) if comps else 0.0,
                    "survivingCount": len(rec.candidate_ids) - len(rec.loser_ids),
                    "apoptosisCount": len(rec.loser_ids),
                }
            )
        return points

    def to_payload(self) -> dict:
        """Render the camelCase CellPayload matching web/lib/types.ts (the consumer).

        Status maps to the frontend's vocabulary: tombstoned lineages are
        ``tombstoned``; among the survivors the highest-fitness one is the
        ``champion`` and the rest are ``alive``. ``fitness`` is normalized to
        [0,1] (judge composite / 10) — the demo labels this "appeal fitness",
        NOT a real-world overturn rate (we have no real outcomes).
        """
        payer, _, diagnosis = self.cell.partition("_")
        fitness = self.fitness_curve()
        apoptosis_total = sum(p["apoptosisCount"] for p in fitness)
        final_max = max((p["maxFitness"] for p in fitness), default=0.0)
        first_max = fitness[0]["maxFitness"] if fitness else 0.0

        survivors = [s for s in self.strategies if s.status != "tombstoned"]
        champion_id = (
            max(survivors, key=lambda s: s.fitness).id if survivors else None
        )

        def _status(s: _StrategyAccum) -> str:
            if s.status == "tombstoned":
                return "tombstoned"
            return "champion" if s.id == champion_id else "alive"

        strategies = [
            {
                "id": s.id,
                "cell": self.cell,
                "generation": s.generation,
                "parentId": s.parent_id,
                "label": _label(s),
                "promptBody": s.body,
                "mutationNote": s.mutation_note,
                "fitness": round(s.fitness / 10.0, 4),
                "tag": "production" if s.status != "tombstoned" else "experimental",
                "status": _status(s),
                "citations": _citations(s.body),
            }
            for s in self.strategies
        ]
        rounds = [
            {
                "id": f"tr_{self.cell}_g{rec.generation}",
                "cell": self.cell,
                "generation": rec.generation,
                "denialId": rec.denial_id,
                "candidateIds": list(rec.candidate_ids),
                "winnerId": rec.winner_id,
                "loserIds": list(rec.loser_ids),
                "judgeRationale": rec.english_feedback,
                "winnerAppeal": rec.winner_appeal,
            }
            for rec in self.generations
        ]
        return {
            "meta": {
                "id": self.cell,
                "payer": payer,
                "diagnosis": diagnosis,
                "baselineOverturn": first_max,
                "currentOverturn": final_max,
                "generations": len(self.generations),
                "populationSize": len(survivors),
                "apoptosisTotal": apoptosis_total,
            },
            "strategies": strategies,
            "rounds": rounds,
            "fitness": fitness,
        }


_CITATION_RE = re.compile(
    r"(?:Aetna )?CPB \d{3,4}|ACC/AHA \d{4}(?:\s*§[\d.]+)?|29 CFR [\d.\-]+"
)


def _citations(body: str) -> list[str]:
    """Extract the policy/guideline citations a strategy preferentially cites."""
    return sorted(set(_CITATION_RE.findall(body)))


def _label(s: _StrategyAccum) -> str:
    if s.parent_id is None:
        return f"G{s.generation} — seed"
    if s.mutation_note:
        return f"G{s.generation} — {s.mutation_note.split(':', 1)[0]}"
    return f"G{s.generation} — mutant"


async def sweep_bodies_and_status(
    nodes: dict[str, _StrategyAccum], phoenix: PhoenixClient
) -> None:
    """Fill body + final status for every strategy from Phoenix.

    production tag resolves → status=production, body from version.
    tombstoned tag resolves → status=tombstoned, body from version.
    else → leave as-is (experimental/unknown).
    """
    for node in nodes.values():
        for tag, status in (("production", "production"), ("tombstoned", "tombstoned")):
            try:
                ver = await phoenix._mcp.call_tool(
                    "get-prompt-version-by-tag",
                    {"prompt_identifier": node.id, "tag_name": tag},
                )
            except PhoenixToolError:
                continue
            node.body = _extract_template_text(ver.get("template"))
            node.status = status
            node.tag = tag
            break


class GenerationalEvolution:
    def __init__(
        self, *, cycle: GerminalCycle, phoenix: PhoenixClient, cell: str, generations: int
    ) -> None:
        self._cycle = cycle
        self._phoenix = phoenix
        self._cell = cell
        self._generations = generations

    async def run(self, *, denial: Denial) -> EvolutionResult:
        records: list[GenerationRecord] = []
        # id -> accumulator. Seeds get added on first sighting (gen 0 candidates);
        # mutants get added when spawned (parent = that gen's winner).
        nodes: dict[str, _StrategyAccum] = {}

        for g in range(self._generations):
            outcome = await self._cycle.run(denial=denial, generation=g)
            records.append(_record(outcome, denial.denial_id))

            score_by_id = dict(outcome.scoreboard)
            # Candidates seen this generation that we haven't recorded yet are
            # seeds (gen 0) — mutants were already recorded when spawned.
            for cid in score_by_id:
                node = nodes.get(cid)
                if node is None:
                    nodes[cid] = _StrategyAccum(
                        id=cid, generation=g, parent_id=None, mutation_note=None,
                        fitness=score_by_id[cid],
                    )
                else:
                    node.fitness = score_by_id[cid]
            # Spawned mutants → children of this generation's winner.
            notes = dict(outcome.mutant_notes)
            for mid in outcome.mutant_ids:
                nodes.setdefault(
                    mid,
                    _StrategyAccum(
                        id=mid, generation=g + 1, parent_id=outcome.winner_id,
                        mutation_note=notes.get(mid),
                    ),
                )
            _log.info(
                "gen %d: winner=%s composite=%.2f tombstoned=%d mutants=%d",
                g, outcome.winner_id, outcome.winner_composite_score,
                len(outcome.tombstoned_ids), len(outcome.mutant_ids),
            )

        await self._sweep_bodies_and_status(nodes)
        return EvolutionResult(
            cell=self._cell,
            generations=tuple(records),
            strategies=tuple(nodes.values()),
        )

    async def _sweep_bodies_and_status(self, nodes: dict[str, _StrategyAccum]) -> None:
        await sweep_bodies_and_status(nodes, self._phoenix)


def _record(outcome: CycleOutcome, denial_id: str) -> GenerationRecord:
    candidate_ids = tuple(pid for pid, _ in outcome.scoreboard)
    loser_ids = tuple(pid for pid in outcome.tombstoned_ids if pid in candidate_ids)
    return GenerationRecord(
        generation=outcome.generation,
        denial_id=denial_id,
        candidate_ids=candidate_ids,
        winner_id=outcome.winner_id,
        winner_composite=outcome.winner_composite_score,
        loser_ids=loser_ids,
        scoreboard=outcome.scoreboard,
        mutant_ids=outcome.mutant_ids,
        mutant_notes=outcome.mutant_notes,
        winner_appeal=outcome.winner_appeal,
        english_feedback=outcome.english_feedback,
    )
