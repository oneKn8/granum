"""Gold dataset of overturned appeals — the antigen for tournament scoring."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GoldAppeal:
    """An exemplar overturned appeal letter. B-cell strategies compete to imitate these."""

    denial_id: str
    appeal_text: str
    outcome: str
    judge_score: int
    citations: list[str] = field(default_factory=list)


def load_gold_appeals(path: str | Path) -> list[GoldAppeal]:
    """Load JSONL gold dataset into a list of GoldAppeal."""
    appeals: list[GoldAppeal] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        appeals.append(
            GoldAppeal(
                denial_id=data["denial_id"],
                appeal_text=data["appeal_text"],
                outcome=data["outcome"],
                judge_score=data["judge_score"],
                citations=data.get("citations", []),
            )
        )
    return appeals
