"""Phoenix client — wraps both MCP tool calls AND REST endpoints.

Phoenix MCP exposes prompt creation, version tagging, dataset writes, and
trace reads. It does NOT expose tag removal or version deletion. Tag
removal is REST-only (DELETE /v1/prompt_versions/{vid}/tags/{tag} -> 204).

Granum's functional apoptosis is implemented here as two operations:
1. Remove 'production' tag via REST (so version is no longer eligible for selection).
2. Add 'tombstoned' tag via MCP (so selection queries can filter on absence).

Both happen in `tombstone()`. The version itself stays in the registry —
audit history is preserved. Path B per the Phoenix MCP audit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class _MCPSession(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class PromptVersion:
    prompt_id: str
    version_id: str
    tags: tuple[str, ...] = ()
    body: str = ""
    name: str = ""


class PhoenixClient:
    """Typed wrapper over arize-phoenix MCP + REST.

    Args:
        mcp_session: An active MCP client session (stdio or SSE transport).
        rest: An httpx.AsyncClient configured with the Phoenix base URL.
        base_url: Phoenix base URL (e.g., "http://localhost:6006" or "https://app.phoenix.arize.com").
    """

    def __init__(
        self,
        *,
        mcp_session: _MCPSession,
        rest: httpx.AsyncClient,
        base_url: str,
    ) -> None:
        self._mcp = mcp_session
        self._rest = rest
        self._base_url = base_url.rstrip("/")

    # === Prompts ===

    async def upsert_prompt(
        self, *, name: str, body: str, tags: tuple[str, ...] = ("experimental",)
    ) -> PromptVersion:
        resp = await self._mcp.call_tool(
            "upsert-prompt",
            {"name": name, "body": body, "tags": list(tags)},
        )
        return PromptVersion(
            prompt_id=resp["promptId"],
            version_id=resp["versionId"],
            tags=tuple(resp.get("tags", [])),
            body=body,
            name=name,
        )

    async def add_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> tuple[str, ...]:
        """Add a tag to a prompt version via MCP.

        Note: `add-prompt-version-tag` is MOVE-SEMANTIC. If `tag` already
        exists on a different version of the same prompt, it is silently
        moved to the new version. Use this as the atomic champion-swap
        primitive: re-tagging `production` automatically demotes the
        prior champion.
        """
        resp = await self._mcp.call_tool(
            "add-prompt-version-tag",
            {"promptId": prompt_id, "versionId": version_id, "tag": tag},
        )
        return tuple(resp.get("tags", []))

    async def remove_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> None:
        """Remove a tag via REST (MCP does not expose this operation).

        Returns silently on 204 OR 404 — 404 means the tag was already
        absent, which is fine for tombstone idempotency.
        """
        url = f"{self._base_url}/v1/prompt_versions/{version_id}/tags/{tag}"
        resp = await self._rest.delete(url)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    async def tombstone(self, prompt_id: str, version_id: str) -> None:
        """Functional apoptosis — Path B.

        1. Remove 'production' tag via REST (no longer in active population).
        2. Add 'tombstoned' tag via MCP (selection queries filter on absence).

        Audit history is preserved — the version itself is immutable and remains
        in Phoenix indefinitely.
        """
        await self.remove_version_tag(prompt_id, version_id, "production")
        await self._mcp.call_tool(
            "add-prompt-version-tag",
            {"promptId": prompt_id, "versionId": version_id, "tag": "tombstoned"},
        )

    async def list_active_prompts(self, *, name_prefix: str) -> list[PromptVersion]:
        """Return prompts that have 'production' tag and NOT 'tombstoned' tag.

        Filtering happens client-side because Phoenix `list-prompts` does
        not support tag filters server-side (per audit).
        """
        resp = await self._mcp.call_tool(
            "list-prompts", {"namePrefix": name_prefix}
        )
        result: list[PromptVersion] = []
        for p in resp.get("prompts", []):
            tags = tuple(p.get("tags", []))
            if "tombstoned" in tags:
                continue
            result.append(
                PromptVersion(
                    prompt_id=p["promptId"],
                    version_id=p["versionId"],
                    tags=tags,
                    body=p.get("body", ""),
                    name=p.get("name", ""),
                )
            )
        return result

    # === Datasets ===

    async def add_dataset_examples(
        self, *, dataset_name: str, examples: list[dict[str, Any]]
    ) -> None:
        """Append outcome examples to a Phoenix dataset (antigen writeback)."""
        await self._mcp.call_tool(
            "add-dataset-examples",
            {"datasetName": dataset_name, "examples": examples},
        )

    # === Spans / traces ===

    async def get_spans(self, *, project_name: str, filter_str: str = "") -> list[dict[str, Any]]:
        """Online introspection of recent spans for a project."""
        resp = await self._mcp.call_tool(
            "get-spans",
            {"projectName": project_name, "filter": filter_str},
        )
        return resp.get("spans", [])
