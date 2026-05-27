"""Antigen drift detector - distribution shift in denial patterns.

When the recent denial distribution drifts >threshold (default 25%) over a
window, the drift signal fires. The driver should re-test the current
champion against the new antigens.

v0.1: feature-vector hash of (cpt_code, icd10_code, denial_reason).
Drift = symmetric set difference fraction between two consecutive windows'
feature-bag distributions.

v0.2: swap in sentence-transformer embeddings + cosine distance.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Deque

from granum.data.denials import Denial


class AntigenDrift:
    """Track per-cell denial pattern stream and detect distribution shift."""

    def __init__(self, *, drift_threshold: float = 0.25) -> None:
        self._threshold = drift_threshold
        self._streams: defaultdict[str, Deque[tuple[str, str, str]]] = defaultdict(
            lambda: deque(maxlen=64)  # keep up to 64 most recent per cell
        )

    @staticmethod
    def _feature_vec(denial: Denial) -> tuple[str, str, str]:
        return (denial.cpt_code, denial.icd10_code, str(denial.denial_reason))

    @staticmethod
    def _cell_id(denial: Denial) -> str:
        return f"{denial.payer}_{denial.diagnosis}"

    async def observe_denial(self, *, denial: Denial) -> None:
        """Record a denial in this cell's pattern stream."""
        self._streams[self._cell_id(denial)].append(self._feature_vec(denial))

    async def is_drifted(self, *, cell: str, window_size: int = 10) -> bool:
        """True if mean-bag distribution shift across the most recent two windows exceeds threshold.

        Requires at least 2*window_size observations to fire.
        """
        stream = list(self._streams[cell])
        if len(stream) < 2 * window_size:
            return False
        recent = stream[-window_size:]
        prior = stream[-(2 * window_size):-window_size]
        recent_counter = Counter(recent)
        prior_counter = Counter(prior)
        total = sum(recent_counter.values()) + sum(prior_counter.values())
        if total == 0:
            return False
        all_keys = set(recent_counter) | set(prior_counter)
        diff = sum(
            abs(recent_counter[k] - prior_counter[k]) for k in all_keys
        )
        # Normalize: max possible diff = total (when bags are disjoint)
        normalized = diff / total
        return normalized >= self._threshold
