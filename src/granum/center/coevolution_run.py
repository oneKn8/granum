"""Co-evolution run harness — drive multiple Red Queen rounds and emit payload.

Mirrors ``granum.center.evolution.GenerationalEvolution`` but for the dual-
population co-evolution driver (``CoEvolutionDriver``).  Maintains two lineage
node dicts (writers and payers) across all rounds, sweeps Phoenix once for
final bodies, and serialises to the ``CoEvolutionState`` shape consumed by
``web/lib/types.ts``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from granum.center.coevolution import CoEvolutionDriver
from granum.center.evolution import _citations, _label, _StrategyAccum, sweep_bodies_and_status
from granum.tools.phoenix_client import PhoenixClient

_log = logging.getLogger(__name__)

# Placeholder timestamps — deterministic; no datetime.now() calls allowed.
_CREATED_AT_PLACEHOLDER = ""
_KILLED_AT_PLACEHOLDER = "1970-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Per-node accumulator (reuses the _StrategyAccum shape from evolution.py)
# ---------------------------------------------------------------------------

# We use _StrategyAccum directly (imported above); it has:
#   id, generation, parent_id, mutation_note, fitness, body, status, tag

# The type alias below makes intent explicit at use-sites.
_CoEvNode = _StrategyAccum


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoEvolutionRunResult:
    cell: str
    writer_nodes: tuple[_CoEvNode, ...]
    payer_nodes: tuple[_CoEvNode, ...]

    def to_payload(self) -> dict:
        """Render ``CoEvolutionState`` camelCase payload for the frontend.

        Status rules (computed independently per population):
        - tombstoned → "tombstoned"
        - non-tombstoned with max fitness → "champion"
        - other non-tombstoned → "alive"

        Fitness: normalized from 0-10 → 0-1 (round 4 dp).
        Tag: "production" if alive/champion else "experimental".
        """
        return {
            "cell": self.cell,
            "writers": _serialize_nodes(self.writer_nodes, self.cell),
            "payers": _serialize_nodes(self.payer_nodes, self.cell),
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class CoEvolutionRun:
    def __init__(
        self,
        *,
        driver: CoEvolutionDriver,
        phoenix: PhoenixClient,
        cell: str,
        rounds: int,
    ) -> None:
        self._driver = driver
        self._phoenix = phoenix
        self._cell = cell
        self._rounds = rounds

    async def run(self) -> CoEvolutionRunResult:
        writers: dict[str, _CoEvNode] = {}
        payers: dict[str, _CoEvNode] = {}

        for round_idx in range(self._rounds):
            result = await self._driver.round()

            # Update writer nodes from scoreboard
            for pid, fitness in result.writer_scoreboard:
                node = writers.get(pid)
                if node is None:
                    writers[pid] = _CoEvNode(
                        id=pid,
                        generation=round_idx,
                        parent_id=None,
                        mutation_note=None,
                        fitness=fitness,
                    )
                else:
                    node.fitness = fitness

            # Update payer nodes from scoreboard
            for pid, fitness in result.payer_scoreboard:
                node = payers.get(pid)
                if node is None:
                    payers[pid] = _CoEvNode(
                        id=pid,
                        generation=round_idx,
                        parent_id=None,
                        mutation_note=None,
                        fitness=fitness,
                    )
                else:
                    node.fitness = fitness

            # Register writer mutants as children of this round's writer winner
            for mid in result.writer_mutant_ids:
                writers.setdefault(
                    mid,
                    _CoEvNode(
                        id=mid,
                        generation=round_idx + 1,
                        parent_id=result.writer_winner_id,
                        mutation_note=None,
                    ),
                )

            # Register payer mutants as children of this round's payer winner
            for mid in result.payer_mutant_ids:
                payers.setdefault(
                    mid,
                    _CoEvNode(
                        id=mid,
                        generation=round_idx + 1,
                        parent_id=result.payer_winner_id,
                        mutation_note=None,
                    ),
                )

            _log.info(
                "round %d: writer_winner=%s payer_winner=%s composite=%.2f "
                "writer_losers=%d payer_losers=%d "
                "writer_mutants=%d payer_mutants=%d",
                round_idx,
                result.writer_winner_id,
                result.payer_winner_id,
                result.defensibility_composite,
                len(result.writer_loser_ids),
                len(result.payer_loser_ids),
                len(result.writer_mutant_ids),
                len(result.payer_mutant_ids),
            )

        await self._sweep_bodies_and_status(writers)
        await self._sweep_bodies_and_status(payers)

        return CoEvolutionRunResult(
            cell=self._cell,
            writer_nodes=tuple(writers.values()),
            payer_nodes=tuple(payers.values()),
        )

    async def _sweep_bodies_and_status(self, nodes: dict[str, _CoEvNode]) -> None:
        await sweep_bodies_and_status(nodes, self._phoenix)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _serialize_nodes(nodes: tuple[_CoEvNode, ...], cell: str) -> list[dict]:
    survivors = [n for n in nodes if n.status != "tombstoned"]
    champion_id = max(survivors, key=lambda n: n.fitness).id if survivors else None

    def _status(n: _CoEvNode) -> str:
        if n.status == "tombstoned":
            return "tombstoned"
        return "champion" if n.id == champion_id else "alive"

    result = []
    for node in nodes:
        status = _status(node)
        result.append({
            "id": node.id,
            "cell": cell,
            "generation": node.generation,
            "parentId": node.parent_id,
            "label": _label(node),
            "promptBody": node.body,
            "mutationNote": node.mutation_note,
            "fitness": round(node.fitness / 10.0, 4),
            "tag": "production" if status != "tombstoned" else "experimental",
            "status": status,
            "citations": _citations(node.body),
            "createdAt": _CREATED_AT_PLACEHOLDER,
            "killedAt": _KILLED_AT_PLACEHOLDER if status == "tombstoned" else None,
        })
    return result


