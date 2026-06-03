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


@pytest.mark.asyncio
async def test_wait_for_active_population_retries_until_visible(monkeypatch):
    """Phoenix eventual-consistency guard: retries until min_count prompts appear."""
    from unittest.mock import AsyncMock as _AsyncMock

    from granum.data.seeds import wait_for_active_population

    obj1 = PromptVersion(prompt_id="p1", version_id="v1", body="b", name="n1")
    obj2 = PromptVersion(prompt_id="p2", version_id="v2", body="b", name="n2")
    obj3 = PromptVersion(prompt_id="p3", version_id="v3", body="b", name="n3")

    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.side_effect = [[], [], [obj1, obj2, obj3]]

    sleep_mock = _AsyncMock()
    monkeypatch.setattr("granum.data.seeds.asyncio.sleep", sleep_mock)

    result = await wait_for_active_population(
        phoenix, name_prefix="aetna_cardiac_payer/", min_count=1
    )

    assert result == [obj1, obj2, obj3]
    assert phoenix.list_active_prompts.await_count == 3
    # slept between the two empty attempts (not after the success)
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_wait_for_active_population_raises_when_never_visible(monkeypatch):
    """Raises RuntimeError when the population never reaches min_count after all attempts."""
    from unittest.mock import AsyncMock as _AsyncMock

    from granum.data.seeds import wait_for_active_population

    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = []

    sleep_mock = _AsyncMock()
    monkeypatch.setattr("granum.data.seeds.asyncio.sleep", sleep_mock)

    with pytest.raises(RuntimeError, match="did not reach 1 active prompt"):
        await wait_for_active_population(
            phoenix, name_prefix="aetna_cardiac_payer/", min_count=1, attempts=3
        )
