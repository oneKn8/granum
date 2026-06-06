"""Synthetic denial generator must produce valid, varied Aetna cardiac denials."""
import pytest

from granum.data.denials import generate_denial, Denial, DenialReason


def test_generate_denial_returns_denial_object():
    d = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    assert isinstance(d, Denial)
    assert d.payer == "aetna"
    assert d.diagnosis == "cardiac"
    assert d.denial_id.startswith("aetna_cardiac_")


def test_generate_denial_deterministic_with_seed():
    a = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    b = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    assert a == b


def test_generate_denial_varied_without_seed():
    seen = {generate_denial(payer="aetna", diagnosis="cardiac").denial_id for _ in range(20)}
    assert len(seen) > 5  # at least 5 distinct denials in 20 draws


def test_denial_has_required_fields():
    d = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)
    assert d.denial_reason in DenialReason.__members__.values()
    assert d.cpt_code
    assert d.icd10_code
    assert d.patient_age_range
    assert len(d.denial_text) > 100  # real-feeling denial copy


def test_generate_denial_united_oncology_from_templates():
    """Non-aetna cells are data-driven from data/{cell}/denial_templates.json."""
    d = generate_denial(payer="united", diagnosis="oncology", seed=7)
    assert isinstance(d, Denial)
    assert d.payer == "united"
    assert d.diagnosis == "oncology"
    assert d.denial_id.startswith("united_oncology_")
    assert d.cpt_code
    assert d.icd10_code
    assert d.denial_reason in DenialReason.__members__.values()
    assert len(d.denial_text) > 50


def test_generate_denial_united_oncology_deterministic():
    a = generate_denial(payer="united", diagnosis="oncology", seed=7)
    b = generate_denial(payer="united", diagnosis="oncology", seed=7)
    assert a == b


def test_generate_denial_unknown_cell_raises():
    with pytest.raises(NotImplementedError):
        generate_denial(payer="bogus", diagnosis="nonsense")
