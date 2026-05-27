import json

import pytest
from unittest.mock import AsyncMock

from granum.adversary.payer_agent import PayerAgent
from granum.adversary.payer_persona import get_persona
from granum.data.denials import Denial, DenialReason


_CANNED_DENIAL_JSON = json.dumps(
    {
        "cpt_code": "93306",
        "icd10_code": "I25.10",
        "denial_reason": "not_medically_necessary",
        "denial_text": (
            "Coverage denied for echocardiogram (CPT 93306) for stable angina "
            "(ICD-10 I25.10). Aetna Clinical Policy Bulletin 0119 requires "
            "documentation of new or worsening symptoms. Submitted records show "
            "stable 12-month course. Member may appeal within 30 days of this "
            "notice by submitting additional clinical documentation."
        ),
    }
)


def _make_agent(mock_client: AsyncMock) -> PayerAgent:
    return PayerAgent(
        client=mock_client,
        model="gemini-3-pro",
        payer="aetna",
        diagnosis="cardiac",
    )


@pytest.mark.asyncio
async def test_deny_returns_denial_with_persona_signature():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    denial = await agent.deny(appeal="my candidate appeal text", persona_id="strict")

    assert isinstance(denial, Denial)
    assert denial.cpt_code == "93306"
    assert denial.icd10_code == "I25.10"
    assert denial.denial_reason == DenialReason.NOT_MEDICALLY_NECESSARY
    assert "Aetna Clinical Policy Bulletin 0119" in denial.denial_text
    assert denial.denial_id.startswith("aetna_cardiac_adv_strict_")


@pytest.mark.asyncio
async def test_deny_passes_persona_system_prompt_to_llm():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    appeal_text = "Provider appeal: patient has new-onset chest pain..."
    await agent.deny(appeal=appeal_text, persona_id="strict")

    assert mock_client.generate.await_count == 1
    prompt = mock_client.generate.await_args.kwargs["prompt"]
    strict_prompt = get_persona("strict").system_prompt
    assert strict_prompt in prompt
    assert appeal_text in prompt


@pytest.mark.asyncio
async def test_deny_uses_temperature_zero_and_provided_model():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    await agent.deny(appeal="some appeal", persona_id="lenient")

    kwargs = mock_client.generate.await_args.kwargs
    assert kwargs["temperature"] == 0.0
    assert kwargs["model"] == "gemini-3-pro"


@pytest.mark.asyncio
async def test_deny_raises_keyerror_on_unknown_persona():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    with pytest.raises(KeyError):
        await agent.deny(appeal="some appeal", persona_id="ghost")


@pytest.mark.asyncio
async def test_deny_id_is_deterministic_for_same_appeal_and_persona():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    d1 = await agent.deny(appeal="identical appeal text", persona_id="strict")
    d2 = await agent.deny(appeal="identical appeal text", persona_id="strict")

    assert d1.denial_id == d2.denial_id


@pytest.mark.asyncio
async def test_deny_id_differs_across_personas_for_same_appeal():
    mock_client = AsyncMock()
    mock_client.generate.return_value = _CANNED_DENIAL_JSON
    agent = _make_agent(mock_client)

    d_strict = await agent.deny(appeal="identical appeal text", persona_id="strict")
    d_lenient = await agent.deny(appeal="identical appeal text", persona_id="lenient")

    assert d_strict.denial_id != d_lenient.denial_id


@pytest.mark.asyncio
async def test_deny_raises_on_invalid_denial_reason_value():
    mock_client = AsyncMock()
    mock_client.generate.return_value = json.dumps(
        {
            "cpt_code": "93306",
            "icd10_code": "I25.10",
            "denial_reason": "completely_invalid",
            "denial_text": "bogus denial text",
        }
    )
    agent = _make_agent(mock_client)

    with pytest.raises(ValueError):
        await agent.deny(appeal="some appeal", persona_id="strict")
