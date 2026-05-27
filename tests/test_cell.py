import pytest
from pathlib import Path

from granum.center.cell import Cell, CellRegistry


def test_cell_aetna_cardiac_paths_resolve():
    cell = Cell(payer="aetna", diagnosis="cardiac")
    assert cell.id == "aetna_cardiac"
    assert cell.denial_templates_path == Path("data/aetna_cardiac/denial_templates.json")
    assert cell.valid_citations_path == Path("data/aetna_cardiac/valid_citations.json")
    assert cell.gold_appeals_path == Path("data/aetna_cardiac/gold_appeals.jsonl")
    assert cell.judge_rubric_path == Path("data/judge_rubric.md")
    assert cell.name_prefix == "aetna_cardiac/"


def test_cell_validates_data_files_exist():
    """Cell.validate() raises if expected data files are absent."""
    cell = Cell(payer="aetna", diagnosis="cardiac")
    # All 4 files exist for aetna_cardiac (Terminal A shipped them)
    cell.validate()  # should not raise


def test_cell_validate_raises_for_missing_data(tmp_path, monkeypatch):
    cell = Cell(payer="nonexistent", diagnosis="payer")
    with pytest.raises(FileNotFoundError):
        cell.validate()


def test_registry_lists_known_cells():
    reg = CellRegistry()
    ids = {c.id for c in reg.all_cells()}
    # v0.1: aetna_cardiac always present. The other 4 declared but data may be missing.
    assert "aetna_cardiac" in ids
    assert "united_oncology" in ids
    assert "anthem_mental_health" in ids
    assert "cigna_ortho" in ids
    assert "humana_endocrinology" in ids


def test_registry_get_by_id():
    reg = CellRegistry()
    cell = reg.get("aetna_cardiac")
    assert cell.payer == "aetna"
    assert cell.diagnosis == "cardiac"


def test_registry_validated_cells_only_returns_those_with_data():
    """Returns cells whose data files all exist. Useful for safely iterating."""
    reg = CellRegistry()
    validated = reg.validated_cells()
    # aetna_cardiac has all files. The other 4 depend on Terminal B's progress.
    ids = {c.id for c in validated}
    assert "aetna_cardiac" in ids
