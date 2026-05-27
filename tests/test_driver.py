import pytest
from unittest.mock import AsyncMock, MagicMock

from granum.center.driver import MultiCellDriver, RoundResult
from granum.center.cell import Cell, CellRegistry
from granum.center.cycle import CycleOutcome
from granum.center.judge import JudgeScore
from granum.data.denials import Denial, DenialReason


def _make_denial(suffix: str) -> Denial:
    return Denial(
        denial_id=f"aetna_cardiac_{suffix}",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="50-55",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text="t",
        submission_date="2026-05-01",
    )


@pytest.mark.asyncio
async def test_driver_runs_cycle_per_validated_cell():
    """One denial per cell → cycle runs for every validated cell."""
    cell = Cell(payer="aetna", diagnosis="cardiac")
    mock_cycle = AsyncMock()
    mock_cycle.run.return_value = CycleOutcome(
        cell="aetna_cardiac",
        denial_id="d1",
        survivors_before_tournament=("bc1",),
        rejected_by_negative_selection=(),
        winner_id="bc1",
        winner_version_id="v1",
        winner_composite_score=8.0,
        tombstoned_ids=(),
        mutant_ids=("m1",),
    )
    cycle_factory = MagicMock(return_value=mock_cycle)

    mock_memory = AsyncMock()
    mock_memory.note_success = MagicMock()  # synchronous
    mock_memory.note_extinction = AsyncMock(return_value=None)

    mock_drift = AsyncMock()
    mock_drift.observe_denial = AsyncMock()
    mock_drift.is_drifted = AsyncMock(return_value=False)

    denial_factory = MagicMock(return_value=_make_denial("d1"))

    registry = MagicMock(spec=CellRegistry)
    registry.validated_cells.return_value = [cell]

    driver = MultiCellDriver(
        registry=registry,
        cycle_factory=cycle_factory,
        memory=mock_memory,
        drift=mock_drift,
        denial_factory=denial_factory,
    )
    result = await driver.run_round()

    assert isinstance(result, RoundResult)
    assert len(result.outcomes) == 1
    mock_cycle.run.assert_called_once()
    mock_memory.note_success.assert_called_once_with(cell="aetna_cardiac")
    mock_drift.observe_denial.assert_called_once()


@pytest.mark.asyncio
async def test_driver_calls_extinction_on_runtime_error():
    """When a cycle raises (no survivors), memory.note_extinction is called and the round continues."""
    cell_a = Cell(payer="aetna", diagnosis="cardiac")
    cell_b = Cell(payer="united", diagnosis="oncology")

    cycle_a = AsyncMock()
    cycle_a.run.side_effect = RuntimeError("No survivors after negative selection")
    cycle_b = AsyncMock()
    cycle_b.run.return_value = CycleOutcome(
        cell="united_oncology",
        denial_id="d2",
        survivors_before_tournament=("bc2",),
        rejected_by_negative_selection=(),
        winner_id="bc2",
        winner_version_id="v1",
        winner_composite_score=7.0,
        tombstoned_ids=(),
        mutant_ids=(),
    )

    # cycle_factory returns different cycles based on cell
    def factory(*, cell):
        return cycle_a if cell.id == "aetna_cardiac" else cycle_b

    mock_memory = AsyncMock()
    mock_memory.note_success = MagicMock()
    mock_memory.note_extinction = AsyncMock(return_value=None)

    mock_drift = AsyncMock()
    mock_drift.observe_denial = AsyncMock()
    mock_drift.is_drifted = AsyncMock(return_value=False)

    denial_factory = MagicMock(side_effect=[_make_denial("a"), _make_denial("b")])

    registry = MagicMock(spec=CellRegistry)
    registry.validated_cells.return_value = [cell_a, cell_b]

    driver = MultiCellDriver(
        registry=registry,
        cycle_factory=factory,
        memory=mock_memory,
        drift=mock_drift,
        denial_factory=denial_factory,
    )
    result = await driver.run_round()

    # cell B completed; cell A extinct
    assert len(result.outcomes) == 1
    assert result.outcomes[0].cell == "united_oncology"
    assert "aetna_cardiac" in result.extinctions
    mock_memory.note_extinction.assert_called_once_with(cell="aetna_cardiac")
    mock_memory.note_success.assert_called_once_with(cell="united_oncology")


@pytest.mark.asyncio
async def test_driver_observes_denial_for_drift_per_cell():
    """Drift observer is called once per cell."""
    cell_a = Cell(payer="aetna", diagnosis="cardiac")
    mock_cycle = AsyncMock()
    mock_cycle.run.return_value = CycleOutcome(
        cell="aetna_cardiac",
        denial_id="d1",
        survivors_before_tournament=("bc1",),
        rejected_by_negative_selection=(),
        winner_id="bc1",
        winner_version_id="v1",
        winner_composite_score=8.0,
        tombstoned_ids=(),
        mutant_ids=(),
    )
    cycle_factory = MagicMock(return_value=mock_cycle)
    mock_memory = AsyncMock()
    mock_memory.note_success = MagicMock()
    mock_memory.note_extinction = AsyncMock(return_value=None)
    mock_drift = AsyncMock()
    mock_drift.observe_denial = AsyncMock()
    mock_drift.is_drifted = AsyncMock(return_value=False)
    denial_factory = MagicMock(return_value=_make_denial("x"))

    registry = MagicMock(spec=CellRegistry)
    registry.validated_cells.return_value = [cell_a]

    driver = MultiCellDriver(
        registry=registry,
        cycle_factory=cycle_factory,
        memory=mock_memory,
        drift=mock_drift,
        denial_factory=denial_factory,
    )
    await driver.run_round()
    mock_drift.observe_denial.assert_called_once()
