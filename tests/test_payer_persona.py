"""Tests for the adversarial payer-persona module (Task 3.1).

These tests are mock-only: they verify the seeded persona registry's
shape and content without invoking any LLM. The runtime LLM-call layer
is exercised in later tasks.
"""
from __future__ import annotations

import pytest

from granum.adversary.payer_persona import (
    SEEDED_PERSONAS,
    get_persona,
)


CANONICAL_IDS = {"strict", "lenient", "formalist", "cost_focused", "evidence_focused"}


def test_exactly_five_personas_seeded() -> None:
    assert len(SEEDED_PERSONAS) == 5


def test_persona_ids_are_canonical_set() -> None:
    assert {p.persona_id for p in SEEDED_PERSONAS} == CANONICAL_IDS


def test_persona_ids_are_unique() -> None:
    ids = [p.persona_id for p in SEEDED_PERSONAS]
    assert len(ids) == len(set(ids))


def test_every_persona_has_substantive_system_prompt() -> None:
    for p in SEEDED_PERSONAS:
        assert len(p.system_prompt) >= 200, (
            f"persona {p.persona_id!r} has short system_prompt ({len(p.system_prompt)} chars)"
        )


def test_every_persona_prompt_mentions_three_structural_elements() -> None:
    for p in SEEDED_PERSONAS:
        prompt = p.system_prompt.lower()
        has_reason = ("denial reason" in prompt) or ("reason code" in prompt)
        has_policy = ("policy" in prompt) or ("citation" in prompt)
        has_appeal = "appeal" in prompt
        assert has_reason, f"persona {p.persona_id!r} missing denial-reason guidance"
        assert has_policy, f"persona {p.persona_id!r} missing policy-citation guidance"
        assert has_appeal, f"persona {p.persona_id!r} missing appeal-rights guidance"


def test_get_persona_returns_matching_persona() -> None:
    assert get_persona("strict").persona_id == "strict"


def test_get_persona_raises_on_unknown() -> None:
    with pytest.raises(KeyError, match="cost_focused"):
        get_persona("foo")
