"""Cell abstraction - parameterized (payer x diagnosis) pair with data paths.

In v0.1, five cells are declared. Only `aetna_cardiac` is guaranteed to
have all data files (curated by Terminal A). The other four (United,
Anthem, Cigna, Humana) are curated by Terminal B in parallel; their data
may or may not be present at any given moment.

Use `CellRegistry.validated_cells()` to iterate only over cells with
complete data - safer than `all_cells()` for runtime loops.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Cell:
    payer: str
    diagnosis: str

    @property
    def id(self) -> str:
        return f"{self.payer}_{self.diagnosis}"

    @property
    def name_prefix(self) -> str:
        return f"{self.id}/"

    @property
    def denial_templates_path(self) -> Path:
        return Path(f"data/{self.id}/denial_templates.json")

    @property
    def valid_citations_path(self) -> Path:
        return Path(f"data/{self.id}/valid_citations.json")

    @property
    def gold_appeals_path(self) -> Path:
        return Path(f"data/{self.id}/gold_appeals.jsonl")

    @property
    def judge_rubric_path(self) -> Path:
        # Shared rubric for v0.1. Per-cell rubric variants in v0.2.
        return Path("data/judge_rubric.md")

    def validate(self) -> None:
        """Raise FileNotFoundError if any expected data file is missing."""
        for p in (
            self.denial_templates_path,
            self.valid_citations_path,
            self.gold_appeals_path,
            self.judge_rubric_path,
        ):
            if not p.exists():
                raise FileNotFoundError(
                    f"Cell {self.id!r} missing data file: {p}"
                )


_DECLARED_CELLS: tuple[Cell, ...] = (
    Cell(payer="aetna", diagnosis="cardiac"),
    Cell(payer="united", diagnosis="oncology"),
    Cell(payer="anthem", diagnosis="mental_health"),
    Cell(payer="cigna", diagnosis="ortho"),
    Cell(payer="humana", diagnosis="endocrinology"),
)


class CellRegistry:
    """In-memory registry of declared cells.

    v0.1: 5 hard-coded cells. v0.2 could load from a config file.
    """

    def __init__(self) -> None:
        self._cells: dict[str, Cell] = {c.id: c for c in _DECLARED_CELLS}

    def all_cells(self) -> list[Cell]:
        """All declared cells (data may or may not exist)."""
        return list(self._cells.values())

    def get(self, cell_id: str) -> Cell:
        return self._cells[cell_id]

    def validated_cells(self) -> list[Cell]:
        """Cells whose data files all exist. Safe to iterate at runtime."""
        result: list[Cell] = []
        for c in self._cells.values():
            try:
                c.validate()
                result.append(c)
            except FileNotFoundError:
                continue
        return result
