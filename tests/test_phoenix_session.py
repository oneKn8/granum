"""Unit tests for phoenix_session bootstrap — env var enforcement only.

Live MCP/REST behavior is not tested here (covered by smoke scripts +
integration runs). This file just guards the env-var contract so failures
are loud and immediate, not deep inside MCP stdio plumbing.
"""
from __future__ import annotations

import pytest

from granum.tools.phoenix_session import phoenix_client_from_env


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
