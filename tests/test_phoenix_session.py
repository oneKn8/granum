"""Unit tests for phoenix_session bootstrap — env var enforcement only.

Live MCP/REST behavior is not tested here (covered by smoke scripts +
integration runs). This file just guards the env-var contract so failures
are loud and immediate, not deep inside MCP stdio plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from granum.tools.phoenix_client import PhoenixToolError
from granum.tools.phoenix_session import _MCPDictAdapter, phoenix_client_from_env


# === _MCPDictAdapter — response normalization (regression guards) ===


@dataclass
class _FakeText:
    text: str


@dataclass
class _FakeResult:
    content: list
    isError: bool = False


class _FakeRaw:
    """Stands in for ClientSession — returns a preset CallToolResult-like object."""

    def __init__(self, result):
        self._result = result

    async def call_tool(self, name, arguments):
        return self._result


@pytest.mark.asyncio
async def test_adapter_parses_bare_array_response():
    """list-prompts returns a bare JSON array; must wrap as {'items': [...]}.

    Regression: the prefix-stripper used to pick the first `{` (inside the array)
    before `[`, slicing into the middle of the array and failing to parse.
    """
    raw = _FakeRaw(_FakeResult(content=[_FakeText('[\n  {"name": "a"},\n  {"name": "b"}\n]')]))
    adapter = _MCPDictAdapter(raw)
    out = await adapter.call_tool("list-prompts", {})
    assert out == {"items": [{"name": "a"}, {"name": "b"}]}


@pytest.mark.asyncio
async def test_adapter_strips_text_prefix_before_object():
    """upsert-prompt prefixes JSON with a sentence; the object must still parse."""
    raw = _FakeRaw(_FakeResult(content=[_FakeText('Successfully created prompt "x":\n{"id": "v1"}')]))
    adapter = _MCPDictAdapter(raw)
    out = await adapter.call_tool("upsert-prompt", {})
    assert out == {"id": "v1"}


@pytest.mark.asyncio
async def test_adapter_raises_on_iserror():
    """A 404 miss (isError=True) must raise PhoenixToolError, not return junk."""
    raw = _FakeRaw(_FakeResult(content=[_FakeText("…/tags/production: 404 Not Found")], isError=True))
    adapter = _MCPDictAdapter(raw)
    with pytest.raises(PhoenixToolError):
        await adapter.call_tool("get-prompt-version-by-tag", {})


@pytest.mark.asyncio
async def test_adapter_wraps_naked_success_string():
    """add-prompt-version-tag returns a naked success sentence (not JSON)."""
    raw = _FakeRaw(_FakeResult(content=[_FakeText('Successfully added tag "production" to prompt version v1')]))
    adapter = _MCPDictAdapter(raw)
    out = await adapter.call_tool("add-prompt-version-tag", {})
    assert out["_raw_text"].startswith("Successfully added tag")


@pytest.mark.asyncio
async def test_raises_when_phoenix_api_key_missing(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://example.invalid")
    with pytest.raises(RuntimeError, match="PHOENIX_API_KEY"):
        async with phoenix_client_from_env():
            pass


@pytest.mark.asyncio
async def test_raises_when_phoenix_collector_endpoint_missing(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "fake")
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="PHOENIX_COLLECTOR_ENDPOINT"):
        async with phoenix_client_from_env():
            pass
