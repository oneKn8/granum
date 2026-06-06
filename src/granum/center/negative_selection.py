"""Negative selection — thymic-style elimination of B-cell strategies with
hallucinated citations or structural defects.

This runs BEFORE the tournament. Strategies that fail are tombstoned at
the gate — they never enter the population's competition for the antigen.

Why: LLM-as-judge can rate plausible-sounding text highly even when the
cited Aetna CPB or guideline does not exist. Structural verification
against a curated valid-citation set is the only defense.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


# Match "Aetna CPB <digits>" with optional ", section X" annotation
_AETNA_CPB_RE = re.compile(r"Aetna\s+CPB\s+(\d{3,5})", re.IGNORECASE)

# Match ACC/AHA <year> with optional section reference
_ACC_AHA_RE = re.compile(
    r"ACC/AHA[/\w]*\s+(\d{4})(?:\s+[^§]*?(?:§|section)\s*[\d.]+)?",
    re.IGNORECASE,
)

# Match CFR refs
_CFR_RE = re.compile(r"(\d{1,2}\s*CFR\s*\d+(?:\.\d+)*(?:-\d+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class NegativeSelectionResult:
    passed: bool
    invalid: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def extract_citations(text: str) -> set[str]:
    """Extract canonical citation IDs from appeal text."""
    cites: set[str] = set()
    for m in _AETNA_CPB_RE.finditer(text):
        cites.add(f"Aetna CPB {int(m.group(1)):04d}")  # normalize to 4-digit
    for m in _ACC_AHA_RE.finditer(text):
        # canonical form: "ACC/AHA <year>"
        year = m.group(1)
        cites.add(f"ACC/AHA {year}")
    for m in _CFR_RE.finditer(text):
        # normalize internal whitespace
        raw = m.group(1)
        normalized = re.sub(r"\s+", " ", raw).strip()
        cites.add(normalized)
    return cites


def _load_valid_set(path: str | Path) -> set[str]:
    data = json.loads(Path(path).read_text())
    return {entry["id"].strip() for entry in data}


def _citations_from_valid_set(text: str, valid: set[str]) -> set[str]:
    """Cell-generic citation detection.

    A cell's own valid_citations.json entry counts as *cited* when its
    (whitespace-normalized) id appears verbatim in the text. This is what lets
    non-aetna cells — whose policy names the Aetna/ACC/CFR regexes cannot match —
    pass negative selection when they cite their real controlling policy. The
    appeal is responding to a denial that names that policy, so a strategy told
    to "cite the controlling policy" reliably echoes it.
    """
    norm_text = re.sub(r"\s+", " ", text).lower()
    hits: set[str] = set()
    for v in valid:
        # Try progressively shorter anchors so a paraphrased citation still
        # matches: the full id, the specific policy title after the last ':'
        # (e.g. "Oncology Medication Clinical Coverage"), and the pre-'§' core.
        anchors = {v, v.split("§")[0].strip()}
        if ":" in v:
            anchors.add(v.split(":")[-1].strip())
        for a in anchors:
            norm_a = re.sub(r"\s+", " ", a).strip().lower()
            if len(norm_a) >= 8 and norm_a in norm_text:
                hits.add(v)
                break
    return hits


def _check_deadline_reference(text: str) -> bool:
    lower = text.lower()
    return (
        "30 days" in lower
        or "30-day" in lower
        or "29 cfr 2560.503-1" in lower
        or "appeal deadline" in lower
        or "reconsideration within" in lower
        or "deadline" in lower
        or "timely" in lower  # "65-day timely-filing window" (UHC commercial)
        or bool(re.search(r"\b\d{1,3}[\s-]?days?\b", lower))  # 65-day / 65 days
    )


def verify_citations(
    text: str, *, valid_set_path: str | Path
) -> NegativeSelectionResult:
    """Run all negative-selection checks against an appeal candidate.

    Returns NegativeSelectionResult.passed=True iff:
    - At least one citation found (via the Aetna/ACC/CFR regexes OR a verbatim
      match against the cell's own valid_citations.json — see
      `_citations_from_valid_set`, which makes this cell-generic)
    - Every regex-extracted citation resolves to the valid set (hallucination guard)
    - Appeal references a deadline (29 CFR 2560.503-1, '30 days', etc.)
    """
    valid = _load_valid_set(valid_set_path)
    regex_found = extract_citations(text)
    # Cell-generic: a cell's real policy names (UnitedHealthcare etc.) the regexes
    # can't parse still count as citations when they appear verbatim in the text.
    valid_hits = _citations_from_valid_set(text, valid)
    found = regex_found | valid_hits

    reasons: list[str] = []
    invalid: list[str] = []

    if not found:
        reasons.append("no_citations_found")

    # Normalize valid set for prefix matching (e.g., "Aetna CPB 0119"
    # matches even if appeal cites "Aetna CPB 0119 §IV.A")
    valid_normalized: set[str] = set()
    for v in valid:
        valid_normalized.add(v)
        # also add prefix form for partial matches
        if "§" in v:
            valid_normalized.add(v.split("§")[0].strip())

    valid_lower = {v.lower() for v in valid_normalized}

    # Only the regex-extracted citations need the hallucination check; valid_hits
    # are valid-set members by construction.
    for c in sorted(regex_found):
        # exact match
        if c in valid_normalized:
            continue
        # case-insensitive exact (for CFR refs)
        if c.lower() in valid_lower:
            continue
        # prefix match (candidate citation is more specific than valid entry)
        if any(c.startswith(v) for v in valid_normalized):
            continue
        invalid.append(c)

    if invalid:
        reasons.append("hallucinated_citations")

    if not _check_deadline_reference(text):
        reasons.append("missing_deadline_reference")

    passed = not reasons

    return NegativeSelectionResult(
        passed=passed,
        invalid=tuple(sorted(invalid)),
        reasons=tuple(reasons),
    )
