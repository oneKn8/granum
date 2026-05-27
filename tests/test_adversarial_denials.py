"""Tests for the adversarial denial factory and its sync adapter.

The factory is a runtime drop-in replacement for the synthetic
`generate_denial`: it rotates round-robin through the 5 seeded payer
personas and seed appeals, calling `PayerAgent.deny` to obtain an
LLM-generated denial per call.

The sync adapter wraps the async factory so the `MultiCellDriver` can
consume it via its `_DenialFactory` Protocol signature.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from granum.adversary.adversarial_denials import (
    AdversarialDenialFactory,
    as_denial_factory,
)
from granum.adversary.payer_agent import PayerAgent
from granum.data.denials import Denial, DenialReason


def _canned_denial(denial_id: str = "aetna_cardiac_adv_strict_abc123") -> Denial:
    return Denial(
        denial_id=denial_id,
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text=(
            "Coverage denied for echocardiogram. Aetna CPB 0119 requires "
            "documentation of new or worsening symptoms. Member may appeal "
            "within 30 days of this notice."
        ),
        submission_date="adversarial",
    )


@pytest.mark.asyncio
async def test_round_robin_persona_rotation_across_six_calls():
    mock_agent = AsyncMock(spec=PayerAgent)
    mock_agent.deny.return_value = _canned_denial()
    factory = AdversarialDenialFactory(
        payer_agent=mock_agent,
        seed_appeals=["appeal-A"],
    )

    for _ in range(6):
        await factory.generate()

    persona_ids = [call.kwargs["persona_id"] for call in mock_agent.deny.call_args_list]
    assert persona_ids == [
        "strict",
        "lenient",
        "formalist",
        "cost_focused",
        "evidence_focused",
        "strict",
    ]


@pytest.mark.asyncio
async def test_round_robin_seed_appeal_rotation_when_more_calls_than_seeds():
    mock_agent = AsyncMock(spec=PayerAgent)
    mock_agent.deny.return_value = _canned_denial()
    factory = AdversarialDenialFactory(
        payer_agent=mock_agent,
        seed_appeals=["appeal-0", "appeal-1"],
    )

    for _ in range(3):
        await factory.generate()

    appeals = [call.kwargs["appeal"] for call in mock_agent.deny.call_args_list]
    assert appeals == ["appeal-0", "appeal-1", "appeal-0"]


def test_factory_requires_non_empty_seed_appeals():
    mock_agent = AsyncMock(spec=PayerAgent)
    with pytest.raises(ValueError, match="seed_appeals"):
        AdversarialDenialFactory(payer_agent=mock_agent, seed_appeals=[])


def _make_mock_agent(payer: str = "aetna", diagnosis: str = "cardiac") -> AsyncMock:
    mock_agent = AsyncMock(spec=PayerAgent)
    # AsyncMock(spec=...) doesn't expose @property descriptors as live
    # attributes; assign explicitly so the adapter validation can read them.
    mock_agent.payer = payer
    mock_agent.diagnosis = diagnosis
    mock_agent.deny.return_value = _canned_denial()
    return mock_agent


def test_adapter_returns_callable_with_correct_signature():
    mock_agent = _make_mock_agent()
    factory_fn = as_denial_factory(
        payer_agent=mock_agent, seed_appeals=["appeal-A"]
    )
    assert callable(factory_fn)
    denial = factory_fn(payer="aetna", diagnosis="cardiac")
    assert isinstance(denial, Denial)


def test_adapter_calls_through_to_factory():
    mock_agent = _make_mock_agent()
    factory_fn = as_denial_factory(
        payer_agent=mock_agent, seed_appeals=["appeal-A"]
    )
    factory_fn(payer="aetna", diagnosis="cardiac")
    assert mock_agent.deny.call_count == 1


def test_adapter_raises_on_cell_mismatch():
    mock_agent = _make_mock_agent(payer="aetna", diagnosis="cardiac")
    factory_fn = as_denial_factory(
        payer_agent=mock_agent, seed_appeals=["appeal-A"]
    )
    with pytest.raises(ValueError):
        factory_fn(payer="united", diagnosis="cardiac")


def test_adapter_raises_on_empty_seed_appeals():
    mock_agent = _make_mock_agent()
    with pytest.raises(ValueError, match="seed_appeals"):
        as_denial_factory(payer_agent=mock_agent, seed_appeals=[])
