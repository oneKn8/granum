"""Cell embedding for cross-cell transfer detection.

v0.1: bag-of-features vector built from denial_templates.json. Each cell's
embedding is a token-frequency vector over the union of:
  - cpt_code values (e.g., "93306", "33533")
  - icd10_code values (e.g., "I25.10", "I50.32")
  - denial_reason values (string form of DenialReason enum)
  - normalized keywords extracted from text_template (lowercase, stripped of
    punctuation, stop-words removed, length >= 4 chars)

Similarity = cosine between two cells' tf-vectors over the union of their
feature spaces.

v0.2 path: swap in sentence-transformers embeddings + cosine on
sentence vectors. Interface stays the same.
"""
from __future__ import annotations

import json
import string
from collections import Counter
from typing import Iterable

from granum.center.cell import CellRegistry


# Minimal stop-word list for clinical denial text
_STOPWORDS: frozenset[str] = frozenset({
    "the", "and", "for", "with", "patient", "denied", "coverage",
    "appeal", "policy", "must", "this", "that", "from", "have", "been",
    "deadline", "days", "submitted", "records", "show", "without",
    "requires", "documented", "appeals", "approved",
})


def _normalize_text(text: str) -> Iterable[str]:
    """Tokenize, lowercase, strip punctuation, length>=4, remove stopwords."""
    cleaned = text.lower().translate(str.maketrans("", "", string.punctuation))
    for token in cleaned.split():
        if len(token) >= 4 and token not in _STOPWORDS:
            yield token


class CellEmbedder:
    """Compute bag-of-features embeddings for cells + pairwise similarity."""

    def __init__(self, *, registry: CellRegistry | None = None) -> None:
        self._registry = registry or CellRegistry()
        self._cache: dict[str, Counter[str]] = {}

    def embed(self, cell_id: str) -> Counter[str]:
        """Return the (cached) token-frequency Counter for a cell."""
        if cell_id in self._cache:
            return self._cache[cell_id]
        cell = self._registry.get(cell_id)
        path = cell.denial_templates_path
        if not path.exists():
            raise FileNotFoundError(
                f"denial templates missing for cell {cell_id}: {path}"
            )
        patterns = json.loads(path.read_text())
        counter: Counter[str] = Counter()
        for p in patterns:
            counter[f"cpt:{p['cpt_code']}"] += 1
            counter[f"icd10:{p['icd10_code']}"] += 1
            counter[f"reason:{p['denial_reason']}"] += 1
            for tok in _normalize_text(p.get("text_template", "")):
                counter[f"tok:{tok}"] += 1
        self._cache[cell_id] = counter
        return counter

    def similarity(self, cell_a: str, cell_b: str) -> float:
        """Cosine similarity in [0,1]. Self-similarity is exactly 1.0."""
        vec_a = self.embed(cell_a)
        vec_b = self.embed(cell_b)
        if cell_a == cell_b:
            return 1.0
        keys = set(vec_a) | set(vec_b)
        dot = sum(vec_a[k] * vec_b[k] for k in keys)
        norm_a = sum(v * v for v in vec_a.values()) ** 0.5
        norm_b = sum(v * v for v in vec_b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def similarity_matrix(
        self, cell_ids: list[str]
    ) -> dict[tuple[str, str], float]:
        """All pairwise similarities for the given cell ids.

        Returns dict keyed by (cell_a, cell_b) with cell_a < cell_b lex order
        for canonical ordering. Diagonal (self) entries omitted.
        """
        result: dict[tuple[str, str], float] = {}
        sorted_ids = sorted(cell_ids)
        for i, a in enumerate(sorted_ids):
            for b in sorted_ids[i + 1:]:
                result[(a, b)] = self.similarity(a, b)
        return result
