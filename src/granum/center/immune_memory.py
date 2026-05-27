"""Immune memory — preserve champion strategies + reactivate on extinction.

Memory B-cells in immunology are long-lived, dormant lymphocytes that
respond rapidly when their antigen reappears. In Granum, a champion
strategy is tagged 'memory_cell' after winning a tournament. It is NOT
in active selection (production tag is also moved when a new champion
arises). When 2 consecutive cycles fail negative selection — i.e., the
active production population is wiped — the most recent memory cell is
reactivated by re-tagging it `production`.

This is the Path B compliant mechanism: the version itself is immutable,
and the tag system tracks all state transitions.
"""
from __future__ import annotations

from granum.tools.phoenix_client import PhoenixClient, PromptVersion


class ImmuneMemory:
    """Track per-cell consecutive extinctions and manage memory-cell tags."""

    _REACTIVATION_THRESHOLD = 2

    def __init__(self, *, phoenix: PhoenixClient) -> None:
        self._phoenix = phoenix
        self._consecutive_extinctions: dict[str, int] = {}

    async def preserve_champion(
        self, *, cell: str, prompt_id: str, version_id: str
    ) -> None:
        """Tag a winning version as 'memory_cell' for long-term preservation."""
        await self._phoenix.add_version_tag(prompt_id, version_id, "memory_cell")

    async def list_memory_cells(self, *, cell: str) -> list[PromptVersion]:
        """Return all PromptVersions tagged `memory_cell` for this cell."""
        # NOTE: list_active_prompts already filters out tombstoned.
        # We filter further by `memory_cell` tag.
        all_active = await self._phoenix.list_active_prompts(
            name_prefix=f"{cell}/"
        )
        return [pv for pv in all_active if "memory_cell" in pv.tags]

    async def reactivate(self, *, cell: str) -> PromptVersion | None:
        """Reactivate the most-recent memory cell by tagging it `production`.

        Returns the reactivated PromptVersion, or None if no memory cells exist.

        The most-recent memory cell is chosen as the LAST entry in
        `list_memory_cells()` — Phoenix list order is creation-time ascending
        in practice. v0.2 could use explicit timestamps once Phoenix exposes them.
        """
        memory_cells = await self.list_memory_cells(cell=cell)
        if not memory_cells:
            return None
        most_recent = memory_cells[-1]
        # add_version_tag('production') is move-semantic — auto-demotes any
        # prior production version of the same prompt name.
        await self._phoenix.add_version_tag(
            most_recent.prompt_id, most_recent.version_id, "production"
        )
        # Reset counter — population is alive again
        self._consecutive_extinctions[cell] = 0
        return most_recent

    async def note_extinction(self, *, cell: str) -> PromptVersion | None:
        """Increment consecutive-extinction counter; reactivate at threshold.

        Returns the reactivated PromptVersion if reactivation fires, else None.
        """
        self._consecutive_extinctions[cell] = (
            self._consecutive_extinctions.get(cell, 0) + 1
        )
        if self._consecutive_extinctions[cell] >= self._REACTIVATION_THRESHOLD:
            return await self.reactivate(cell=cell)
        return None

    def note_success(self, *, cell: str) -> None:
        """Reset the consecutive-extinction counter (synchronous)."""
        self._consecutive_extinctions[cell] = 0
