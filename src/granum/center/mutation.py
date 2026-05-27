"""Structured mutation operators for clonal expansion.

Mutations are deliberately small and structured. There is no
`prompt_rewrite` operator. Affinity maturation works by incremental
refinement, not regeneration. Large rewrites would break the lineage
metaphor — a child should be recognizably descended from its parent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MutationKind(StrEnum):
    CITATION_SWAP = "citation_swap"
    PARAGRAPH_REFRAME = "paragraph_reframe"
    GUIDELINE_CHANGE = "guideline_change"
    EVIDENCE_REORDER = "evidence_reorder"


@dataclass(frozen=True)
class Mutation:
    kind: MutationKind
    target: str
    replacement: str


def apply_mutation(parent: str, mutation: Mutation) -> str:
    """Apply a mutation to a parent appeal text.

    Replaces exactly one occurrence (first) of the target with the replacement.
    Validates that the mutation kind is recognized and the target exists.

    Raises:
        ValueError if the mutation kind is unknown or target is not in parent.
    """
    if mutation.kind not in MutationKind.__members__.values():
        raise ValueError(f"unknown mutation kind {mutation.kind!r}")
    if mutation.target not in parent:
        raise ValueError(f"target {mutation.target!r} not found in parent")
    return parent.replace(mutation.target, mutation.replacement, 1)
