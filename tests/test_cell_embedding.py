"""Tests for CellEmbedder - bag-of-features cosine similarity over cells."""
from __future__ import annotations

import pytest

from granum.transfer.embedding import CellEmbedder


def test_embed_returns_nonempty_counter_for_aetna_cardiac() -> None:
    embedder = CellEmbedder()
    counter = embedder.embed("aetna_cardiac")
    # 10 patterns * (cpt + icd10 + reason) => at least 10 unique features in practice.
    assert len(counter) >= 10


def test_embed_uses_cache_on_repeat_calls() -> None:
    embedder = CellEmbedder()
    first = embedder.embed("aetna_cardiac")
    second = embedder.embed("aetna_cardiac")
    assert id(first) == id(second)


def test_embed_raises_on_unknown_cell() -> None:
    embedder = CellEmbedder()
    with pytest.raises(KeyError):
        embedder.embed("foo_bar")


def test_self_similarity_is_one() -> None:
    embedder = CellEmbedder()
    assert embedder.similarity("aetna_cardiac", "aetna_cardiac") == 1.0


def test_similarity_is_symmetric() -> None:
    embedder = CellEmbedder()
    ab = embedder.similarity("aetna_cardiac", "cigna_ortho")
    ba = embedder.similarity("cigna_ortho", "aetna_cardiac")
    assert abs(ab - ba) < 1e-9


def test_similarity_is_in_zero_one_range() -> None:
    embedder = CellEmbedder()
    cell_ids = [
        "aetna_cardiac",
        "united_oncology",
        "anthem_mental_health",
        "cigna_ortho",
        "humana_endocrinology",
    ]
    for i, a in enumerate(cell_ids):
        for b in cell_ids[i + 1:]:
            sim = embedder.similarity(a, b)
            assert 0.0 <= sim <= 1.0, f"sim({a},{b})={sim} out of range"


def test_aetna_cardiac_more_similar_to_self_than_to_cigna_ortho() -> None:
    embedder = CellEmbedder()
    self_sim = embedder.similarity("aetna_cardiac", "aetna_cardiac")
    cross_sim = embedder.similarity("aetna_cardiac", "cigna_ortho")
    assert self_sim > cross_sim


def test_similarity_matrix_returns_canonical_pairs() -> None:
    embedder = CellEmbedder()
    matrix = embedder.similarity_matrix(
        ["aetna_cardiac", "cigna_ortho", "united_oncology"]
    )
    assert len(matrix) == 3
    assert set(matrix.keys()) == {
        ("aetna_cardiac", "cigna_ortho"),
        ("aetna_cardiac", "united_oncology"),
        ("cigna_ortho", "united_oncology"),
    }
    # No self pairs.
    for a, b in matrix.keys():
        assert a != b
        assert a < b
