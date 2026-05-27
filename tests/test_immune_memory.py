import pytest
from unittest.mock import AsyncMock

from granum.center.immune_memory import ImmuneMemory
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_preserve_champion_adds_memory_cell_tag():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.add_version_tag.return_value = ("production", "memory_cell")
    mem = ImmuneMemory(phoenix=phoenix)
    await mem.preserve_champion(cell="aetna_cardiac", prompt_id="bc1", version_id="v3")
    phoenix.add_version_tag.assert_called_once_with("bc1", "v3", "memory_cell")


@pytest.mark.asyncio
async def test_list_memory_cells_returns_only_memory_tagged():
    phoenix = AsyncMock(spec=PhoenixClient)
    # phoenix.list_active_prompts already filters out tombstoned. We need a
    # separate "list_prompts_with_tag" capability; for v0.1 we'll piggyback
    # on list_active_prompts and filter client-side.
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="bc1", version_id="v1", tags=("production",), body="a"),
        PromptVersion(prompt_id="bc2", version_id="v2", tags=("production", "memory_cell"), body="b"),
        PromptVersion(prompt_id="bc3", version_id="v1", tags=("experimental",), body="c"),
        PromptVersion(prompt_id="bc4", version_id="v5", tags=("memory_cell",), body="d"),
    ]
    mem = ImmuneMemory(phoenix=phoenix)
    cells = await mem.list_memory_cells(cell="aetna_cardiac")
    assert {pv.prompt_id for pv in cells} == {"bc2", "bc4"}


@pytest.mark.asyncio
async def test_reactivate_returns_none_if_no_memory_cells():
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = []
    mem = ImmuneMemory(phoenix=phoenix)
    result = await mem.reactivate(cell="aetna_cardiac")
    assert result is None


@pytest.mark.asyncio
async def test_reactivate_picks_most_recent_memory_cell_and_promotes():
    phoenix = AsyncMock(spec=PhoenixClient)
    # Two memory cells — should pick the second (assuming creation_time ordering)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="bc_old", version_id="v1", tags=("memory_cell",), body="a"),
        PromptVersion(prompt_id="bc_new", version_id="v3", tags=("memory_cell",), body="b"),
    ]
    phoenix.add_version_tag.return_value = ("production", "memory_cell")
    mem = ImmuneMemory(phoenix=phoenix)
    result = await mem.reactivate(cell="aetna_cardiac")
    assert result is not None
    # 'production' added — list order tail = newer
    phoenix.add_version_tag.assert_called_once_with("bc_new", "v3", "production")


@pytest.mark.asyncio
async def test_record_extinction_event_then_reactivate_after_2():
    """Track consecutive extinction events; reactivate only after 2nd."""
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="bc_mem", version_id="v1", tags=("memory_cell",), body="m"),
    ]
    phoenix.add_version_tag.return_value = ("production", "memory_cell")
    mem = ImmuneMemory(phoenix=phoenix)
    # First extinction
    triggered_1 = await mem.note_extinction(cell="aetna_cardiac")
    assert triggered_1 is None  # not yet reactivated
    # Second extinction
    triggered_2 = await mem.note_extinction(cell="aetna_cardiac")
    assert triggered_2 is not None  # reactivated now
    phoenix.add_version_tag.assert_called_once()


@pytest.mark.asyncio
async def test_extinction_counter_resets_on_successful_cycle():
    """A successful cycle (note_success) resets the consecutive-extinction counter."""
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.list_active_prompts.return_value = [
        PromptVersion(prompt_id="bc_mem", version_id="v1", tags=("memory_cell",), body="m"),
    ]
    mem = ImmuneMemory(phoenix=phoenix)
    await mem.note_extinction(cell="aetna_cardiac")
    mem.note_success(cell="aetna_cardiac")  # synchronous reset
    # After reset, one more extinction shouldn't trigger reactivation
    result = await mem.note_extinction(cell="aetna_cardiac")
    assert result is None
