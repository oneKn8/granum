"""Unit tests for the shared seed bank + reset helper (granum.data.seeds)."""
from unittest.mock import AsyncMock

import pytest

from granum.adversary.payer_persona import SEEDED_PERSONAS
from granum.data.seeds import reset_cell, seed_cell, seed_payers
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_seed_cell_seeds_three_when_empty():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = []
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id=f"id{i}", version_id="v", body="b", name="n")
        for i in range(3)
    ]
    ids = await seed_cell(phoenix, cell="aetna_cardiac")
    assert len(ids) == 3
    assert phoenix.upsert_prompt.await_count == 3
    # seeded as production
    for call in phoenix.upsert_prompt.await_args_list:
        assert call.kwargs["tags"] == ("production",)


@pytest.mark.asyncio
async def test_seed_cell_noop_when_already_seeded():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="x", version_id="v")
    ]
    ids = await seed_cell(phoenix, cell="aetna_cardiac")
    assert ids == []
    phoenix.upsert_prompt.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_cell_unknown_cell_raises():
    phoenix = AsyncMock(spec=PhoenixClient)
    with pytest.raises(KeyError):
        await seed_cell(phoenix, cell="nonexistent_cell")


@pytest.mark.asyncio
async def test_reset_cell_deletes_only_matching_prefix():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_all_prompts.return_value = [
        {"name": "aetna_cardiac__bcell_1", "id": "P1"},
        {"name": "aetna_cardiac__g1m0", "id": "P2"},
        {"name": "other_cell__x", "id": "P9"},
    ]
    n = await reset_cell(phoenix, cell="aetna_cardiac")
    assert n == 2
    deleted = {c.args[0] for c in phoenix.delete_prompt.await_args_list}
    assert deleted == {"P1", "P2"}


@pytest.mark.asyncio
async def test_seed_payers_seeds_one_prompt_per_persona():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = []
    phoenix.upsert_prompt.side_effect = [
        PromptVersion(prompt_id=f"pid{i}", version_id="v", body="b", name="n")
        for i in range(len(SEEDED_PERSONAS))
    ]
    ids = await seed_payers(phoenix, cell="aetna_cardiac")
    assert len(ids) == len(SEEDED_PERSONAS)
    assert phoenix.upsert_prompt.await_count == len(SEEDED_PERSONAS)
    for i, call in enumerate(phoenix.upsert_prompt.await_args_list):
        persona = SEEDED_PERSONAS[i]
        assert call.kwargs["name"] == f"aetna_cardiac_payer/baseline_{persona.persona_id}"
        assert call.kwargs["body"] == persona.system_prompt
        assert call.kwargs["tags"] == ("production",)
    assert ids == [f"pid{i}" for i in range(len(SEEDED_PERSONAS))]


@pytest.mark.asyncio
async def test_seed_payers_is_noop_when_already_seeded():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="x", version_id="v")
    ]
    ids = await seed_payers(phoenix, cell="aetna_cardiac")
    assert ids == []
    phoenix.upsert_prompt.assert_not_awaited()
