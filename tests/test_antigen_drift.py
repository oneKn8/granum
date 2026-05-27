import pytest

from granum.center.antigen_drift import AntigenDrift
from granum.data.denials import Denial, DenialReason


def _make_denial(*, cpt: str, icd10: str, reason: DenialReason, id_suffix: str = "x") -> Denial:
    return Denial(
        denial_id=f"aetna_cardiac_test_{id_suffix}",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code=cpt,
        icd10_code=icd10,
        patient_age_range="50-55",
        denial_reason=reason,
        denial_text="test denial text",
        submission_date="2026-05-01",
    )


@pytest.mark.asyncio
async def test_no_drift_before_window_filled():
    drift = AntigenDrift()
    for i in range(5):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=str(i))
        )
    assert await drift.is_drifted(cell="aetna_cardiac", window_size=10) is False


@pytest.mark.asyncio
async def test_no_drift_when_distribution_stable():
    drift = AntigenDrift()
    # 20 identical denials -> no drift
    for i in range(20):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=str(i))
        )
    assert await drift.is_drifted(cell="aetna_cardiac", window_size=10) is False


@pytest.mark.asyncio
async def test_drift_fires_when_distribution_shifts():
    drift = AntigenDrift()
    # Window 1 (oldest 10): one feature combo
    for i in range(10):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=f"old{i}")
        )
    # Window 2 (newest 10): totally different feature combo
    for i in range(10):
        await drift.observe_denial(
            denial=_make_denial(cpt="33533", icd10="I35.0", reason=DenialReason.STEP_THERAPY_REQUIRED, id_suffix=f"new{i}")
        )
    assert await drift.is_drifted(cell="aetna_cardiac", window_size=10) is True


@pytest.mark.asyncio
async def test_drift_not_fired_below_threshold():
    drift = AntigenDrift(drift_threshold=0.25)
    # Window 1: 10 of feature A
    for i in range(10):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=f"a{i}")
        )
    # Window 2: 9 of feature A + 1 of feature B (10% shift, below 25%)
    for i in range(9):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=f"a2{i}")
        )
    await drift.observe_denial(
        denial=_make_denial(cpt="33533", icd10="I35.0", reason=DenialReason.STEP_THERAPY_REQUIRED, id_suffix="b1")
    )
    assert await drift.is_drifted(cell="aetna_cardiac", window_size=10) is False


@pytest.mark.asyncio
async def test_drift_isolated_per_cell():
    drift = AntigenDrift()
    # 20 stable for aetna_cardiac
    for i in range(20):
        await drift.observe_denial(
            denial=_make_denial(cpt="93306", icd10="I25.10", reason=DenialReason.NOT_MEDICALLY_NECESSARY, id_suffix=f"a{i}")
        )
    # Different cell ('united_oncology') should not be affected
    assert await drift.is_drifted(cell="united_oncology", window_size=10) is False
