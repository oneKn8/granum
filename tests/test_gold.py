"""Gold dataset of overturned Aetna cardiac appeals must load + validate."""
from pathlib import Path

from granum.data.gold import GoldAppeal, load_gold_appeals


def test_gold_dataset_loads():
    fixture = Path("data/aetna_cardiac/gold_appeals.jsonl")
    appeals = load_gold_appeals(fixture)
    assert len(appeals) == 12
    for a in appeals:
        assert isinstance(a, GoldAppeal)
        assert a.outcome == "overturned"
        assert a.judge_score >= 7
        assert len(a.citations) >= 1
        assert len(a.appeal_text) > 200  # real-feeling, not stubs


def test_gold_dataset_unique_denial_ids():
    appeals = load_gold_appeals(Path("data/aetna_cardiac/gold_appeals.jsonl"))
    ids = [a.denial_id for a in appeals]
    assert len(set(ids)) == len(ids)
