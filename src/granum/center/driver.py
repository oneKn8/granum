"""Multi-cell driver — runs one round of GerminalCycle across all validated cells.

Integrates immune memory + antigen drift hooks:
- Per cell, generate a denial and observe via AntigenDrift.
- Run cycle. On success: note_success in memory (reset extinction counter).
- On RuntimeError ("No survivors..."): note_extinction; memory may reactivate
  a memory_cell after the 2nd consecutive extinction.

Returns aggregated `RoundResult` summarizing successes + extinctions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

from granum.center.antigen_drift import AntigenDrift
from granum.center.cell import Cell, CellRegistry
from granum.center.cycle import CycleOutcome, GerminalCycle
from granum.center.immune_memory import ImmuneMemory
from granum.data.denials import Denial


_log = logging.getLogger(__name__)


class _CycleFactory(Protocol):
    def __call__(self, *, cell: Cell) -> GerminalCycle: ...


class _DenialFactory(Protocol):
    def __call__(self, *, payer: str, diagnosis: str) -> Denial: ...


@dataclass(frozen=True)
class RoundResult:
    outcomes: tuple[CycleOutcome, ...]
    extinctions: tuple[str, ...]  # cell ids that hit no-survivors


class MultiCellDriver:
    def __init__(
        self,
        *,
        registry: CellRegistry,
        cycle_factory: _CycleFactory,
        memory: ImmuneMemory,
        drift: AntigenDrift,
        denial_factory: _DenialFactory,
    ) -> None:
        self._registry = registry
        self._cycle_factory = cycle_factory
        self._memory = memory
        self._drift = drift
        self._denial_factory = denial_factory

    async def run_round(self) -> RoundResult:
        outcomes: list[CycleOutcome] = []
        extinctions: list[str] = []
        for cell in self._registry.validated_cells():
            denial = self._denial_factory(payer=cell.payer, diagnosis=cell.diagnosis)
            await self._drift.observe_denial(denial=denial)
            cycle = self._cycle_factory(cell=cell)
            try:
                outcome = await cycle.run(denial=denial)
            except RuntimeError as e:
                _log.warning("Cell %s extinct this round: %s", cell.id, e)
                extinctions.append(cell.id)
                await self._memory.note_extinction(cell=cell.id)
                continue
            self._memory.note_success(cell=cell.id)
            outcomes.append(outcome)
        return RoundResult(
            outcomes=tuple(outcomes),
            extinctions=tuple(extinctions),
        )
