from granum.center.negative_selection import (
    extract_citations,
    verify_citations,
    NegativeSelectionResult,
)


def test_extract_finds_aetna_cpb_references():
    text = "Per Aetna CPB 0119 section IV.A, the procedure is covered."
    cites = extract_citations(text)
    assert any("0119" in c for c in cites)


def test_extract_finds_acc_aha_with_section():
    text = "ACC/AHA 2021 §6.2 Class IIa supports the request."
    cites = extract_citations(text)
    assert any("ACC/AHA 2021" in c for c in cites)


def test_verify_accepts_real_citations():
    text = (
        "Per Aetna CPB 0119 section IV.A, repeat echocardiography is medically "
        "necessary when documented change in clinical status occurs. ACC/AHA 2021 "
        "§6.2 Class IIa supports. Per 29 CFR 2560.503-1 we request reconsideration "
        "within 30 days."
    )
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert isinstance(result, NegativeSelectionResult)
    assert result.passed
    assert len(result.invalid) == 0


def test_verify_rejects_hallucinated_cpb():
    text = "Per Aetna CPB 9999 the procedure is approved. 30 days appeal deadline."
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert not result.passed
    assert any("9999" in c for c in result.invalid)
    assert "hallucinated_citations" in result.reasons


def test_verify_rejects_no_citations_at_all():
    text = "We disagree with the denial. Please reconsider."
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert not result.passed
    assert "no_citations_found" in result.reasons


def test_verify_rejects_missing_appeal_deadline_reference():
    """Appeal must reference 30-day deadline language (29 CFR 2560.503-1 procedural compliance)."""
    text = "Per Aetna CPB 0119 the procedure is covered. ACC/AHA 2021 §6.2 applies."
    # Missing deadline language
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert not result.passed
    assert "missing_deadline_reference" in result.reasons
