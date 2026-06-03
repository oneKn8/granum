"""Unit tests for phoenix_session bootstrap — env var enforcement + retry logic.

Live MCP/REST behavior is not tested here (covered by smoke scripts +
integration runs). This file guards:
  - env-var contract: failures are loud and immediate
  - _MCPDictAdapter retry logic: transient 5xx/timeout errors are retried,
    genuine 4xx errors are NOT retried (preserves tag-miss semantics)
"""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

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


# === _MCPDictAdapter retry logic ===


@dataclass
class _FakeText2:
    text: str


@dataclass
class _FakeResult2:
    content: list
    isError: bool = False


def _transient_error_result(text: str) -> _FakeResult2:
    return _FakeResult2(content=[_FakeText2(text)], isError=True)


def _success_result(json_text: str) -> _FakeResult2:
    return _FakeResult2(content=[_FakeText2(json_text)], isError=False)


@pytest.mark.asyncio
async def test_call_tool_retries_on_transient_500_then_succeeds(monkeypatch):
    """500 Internal Server Error is transient; should retry and return success."""
    call_count = 0

    async def fake_call_tool(name, arguments):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return _transient_error_result("500 Internal Server Error")
        return _success_result('{"id": "p1"}')

    class FakeRaw:
        async def call_tool(self, name, arguments):
            return await fake_call_tool(name, arguments)

    adapter = _MCPDictAdapter(FakeRaw())
    sleep_mock = AsyncMock()
    with patch("granum.tools.phoenix_session.asyncio.sleep", sleep_mock):
        result = await adapter.call_tool("list-prompts", {})

    assert result == {"id": "p1"}
    assert call_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_call_tool_does_not_retry_genuine_404(monkeypatch):
    """404 not found is a genuine miss — must raise PhoenixToolError after 1 call."""
    call_count = 0

    class FakeRaw:
        async def call_tool(self, name, arguments):
            nonlocal call_count
            call_count += 1
            return _transient_error_result("404 not found")

    adapter = _MCPDictAdapter(FakeRaw())
    sleep_mock = AsyncMock()
    with patch("granum.tools.phoenix_session.asyncio.sleep", sleep_mock):
        with pytest.raises(PhoenixToolError):
            await adapter.call_tool("get-prompt-version-by-tag", {"tag": "production"})

    assert call_count == 1
    sleep_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_call_tool_retries_on_transport_exception(monkeypatch):
    """Transport-level exceptions (connection reset) are transient and should retry."""
    call_count = 0

    class FakeRaw:
        async def call_tool(self, name, arguments):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("connection reset")
            return _success_result('{"id": "p2"}')

    adapter = _MCPDictAdapter(FakeRaw())
    sleep_mock = AsyncMock()
    with patch("granum.tools.phoenix_session.asyncio.sleep", sleep_mock):
        result = await adapter.call_tool("get-prompt", {})

    assert result == {"id": "p2"}
    assert call_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_call_tool_gives_up_after_max_attempts_on_500(monkeypatch):
    """When all attempts are exhausted on a transient 503, raises PhoenixToolError."""
    call_count = 0

    class FakeRaw:
        async def call_tool(self, name, arguments):
            nonlocal call_count
            call_count += 1
            return _transient_error_result("503 Service Unavailable")

    monkeypatch.setenv("GRANUM_MCP_MAX_ATTEMPTS", "2")
    adapter = _MCPDictAdapter(FakeRaw())
    sleep_mock = AsyncMock()
    with patch("granum.tools.phoenix_session.asyncio.sleep", sleep_mock):
        with pytest.raises(PhoenixToolError):
            await adapter.call_tool("list-prompts", {})

    assert call_count == 2
