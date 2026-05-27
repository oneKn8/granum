"""Deterministic, seed-based mutation proposer (v0.1).

Uses a curated pool of:
- Aetna CPB swap pairs (real CPB numbers from valid_citations.json)
- ACC/AHA guideline swap pairs
- Paragraph reframe pairs (common appeal-language improvements)

When no applicable mutation is found in the parent, falls back to an
identity (no-op) mutation. The cycle orchestrator skips no-op mutants.

v0.2 upgrade path: replace this deterministic proposer with an LLM-driven
one that reads the judge's English feedback and proposes a targeted
mutation. The Protocol signature in cycle.py supports both implementations
via dependency injection — no changes needed downstream.
"""
from __future__ import annotations

import random

from granum.center.mutation import Mutation, MutationKind


# Curated swap pairs. All Aetna CPBs match valid_citations.json.
_CITATION_SWAPS: list[tuple[str, str]] = [
    ("Aetna CPB 0119", "Aetna CPB 0286"),
    ("Aetna CPB 0119", "Aetna CPB 0353"),
    ("Aetna CPB 0286", "Aetna CPB 0353"),
    ("Aetna CPB 0353", "Aetna CPB 0535"),
    ("Aetna CPB 0535", "Aetna CPB 0286"),
    ("Aetna CPB 0218", "Aetna CPB 0379"),
    ("ACC/AHA 2021", "ACC/AHA 2023"),
    ("ACC/AHA 2021 Chronic Coronary Disease", "ACC/AHA 2020 Heart Failure"),
    ("ACC/AHA 2020 Heart Failure", "ACC/AHA 2021 Chronic Coronary Disease"),
]


_PARAGRAPH_REFRAMES: list[tuple[str, str]] = [
    (
        "The procedure is medically necessary",
        "The submitted clinical documentation demonstrates medical necessity exceeding policy threshold",
    ),
    (
        "we appeal",
        "we respectfully appeal",
    ),
    (
        "We disagree with the denial",
        "Submitted records establish the clinical criteria specified in the policy",
    ),
    (
        "the procedure is covered",
        "coverage is supported per the policy criteria documented above",
    ),
    (
        "Coverage applies",
        "Coverage applies under the specific clinical-necessity threshold cited",
    ),
]


def propose_mutations(
    *, parent: str, n: int, seed: int | None = None
) -> list[Mutation]:
    """Propose `n` small structured mutations on a parent appeal text.

    Each mutation is one of:
    - CITATION_SWAP: swap one Aetna CPB or ACC/AHA reference for another in the valid set.
    - PARAGRAPH_REFRAME: replace one common appeal phrasing with a stronger variant.

    If no applicable mutation can be found in the parent for a given draw,
    falls back to an identity mutation (target == replacement); the cycle
    orchestrator skips these.

    Args:
        parent: The parent appeal text.
        n: Number of mutations to propose.
        seed: Deterministic seed; None for random.

    Returns:
        List of `n` Mutation instances (some may be no-ops if parent is
        not amenable to the curated pool).
    """
    if n <= 0:
        return []
    rng = random.Random(seed)
    proposals: list[Mutation] = []
    for _ in range(n):
        kind = rng.choice(
            [MutationKind.CITATION_SWAP, MutationKind.PARAGRAPH_REFRAME]
        )
        if kind is MutationKind.CITATION_SWAP:
            applicable = [(t, r) for t, r in _CITATION_SWAPS if t in parent]
            if applicable:
                t, r = rng.choice(applicable)
                proposals.append(
                    Mutation(kind=MutationKind.CITATION_SWAP, target=t, replacement=r)
                )
                continue
            # Fall through to paragraph reframe
            kind = MutationKind.PARAGRAPH_REFRAME

        if kind is MutationKind.PARAGRAPH_REFRAME:
            applicable_p = [(t, r) for t, r in _PARAGRAPH_REFRAMES if t in parent]
            if applicable_p:
                t, r = rng.choice(applicable_p)
                proposals.append(
                    Mutation(
                        kind=MutationKind.PARAGRAPH_REFRAME, target=t, replacement=r
                    )
                )
                continue

        # No applicable mutation found — emit identity no-op
        # (cycle orchestrator skips these)
        if len(parent) >= 5:
            slice_ = parent[:5]
            proposals.append(
                Mutation(
                    kind=MutationKind.CITATION_SWAP,
                    target=slice_,
                    replacement=slice_,
                )
            )
        else:
            # Parent too short — fabricate a trivial no-op
            proposals.append(
                Mutation(
                    kind=MutationKind.CITATION_SWAP,
                    target="",
                    replacement="",
                )
            )

    return proposals
