"""Live Phoenix session bootstrap — wires PhoenixClient to a real Phoenix endpoint.

Two transports get configured:
1. **MCP stdio** via `@arizeai/phoenix-mcp` (npx-launched Node subprocess). Used for
   all tool calls listed in `research/phoenix-mcp-audit.md` (10 prompt tools, 7
   dataset tools, 8 tracing tools, 2 misc — 27 total).
2. **REST HTTPS** via httpx. Required because tag REMOVAL on prompt versions is
   not exposed via MCP (audit-verified Path B). The REST client uses
   `Authorization: Bearer <PHOENIX_API_KEY>` per Phoenix Cloud's documented
   auth scheme. We ALSO send the legacy `api_key` header for compatibility with
   older Phoenix versions, mirroring what `phoenix.otel.register` does.

Usage:

    from granum.tools.phoenix_session import phoenix_client_from_env

    async with phoenix_client_from_env() as phoenix:
        prompts = await phoenix.list_active_prompts(name_prefix="aetna_cardiac/")
        ...

Env vars required:
- PHOENIX_API_KEY        — JWT from Phoenix Cloud Settings → API Keys
- PHOENIX_COLLECTOR_ENDPOINT — e.g. https://app.phoenix.arize.com/s/<space>

Env vars optional:
- PHOENIX_MCP_PACKAGE    — npm package spec, defaults to "@arizeai/phoenix-mcp@latest"
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from granum.tools.phoenix_client import PhoenixClient, PhoenixToolError


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Source .env or export it before running."
        )
    return value


class _MCPDictAdapter:
    """Thin wrapper that exposes `call_tool(name, args) -> dict`.

    The MCP Python SDK's `ClientSession.call_tool` returns a `CallToolResult`
    Pydantic object whose payload lives in `.content` as a list of content
    items (typically a single `TextContent` containing a JSON string).

    PhoenixClient (Phase 1.3) was authored against a mocked session that
    returned plain dicts. This adapter bridges the two so PhoenixClient's
    code path is unchanged: tests mock it with dicts, live code uses this
    adapter to unpack `CallToolResult.content[0].text` -> JSON -> dict.

    Tools that return no content (None / empty) → returns {}.
    """

    # Retry knobs — read from env so tests can override without patching internals.
    _MAX_ATTEMPTS = int(os.getenv("GRANUM_MCP_MAX_ATTEMPTS", "4"))
    _BASE_BACKOFF = float(os.getenv("GRANUM_MCP_BASE_BACKOFF", "2.0"))
    _MAX_BACKOFF = 30.0

    # Keywords that identify a TRANSIENT server-side error (case-insensitive).
    _TRANSIENT_MARKERS = (
        "500",
        "502",
        "503",
        "504",
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "timeout",
        "timed out",
        "temporarily",
    )

    def __init__(self, raw: ClientSession) -> None:
        self._raw = raw
        # Re-read knobs at construction time so monkeypatch/env changes in tests
        # are picked up per-adapter-instance.
        self._max_attempts = int(os.getenv("GRANUM_MCP_MAX_ATTEMPTS", "4"))
        self._base_backoff = float(os.getenv("GRANUM_MCP_BASE_BACKOFF", "2.0"))

    @staticmethod
    def _is_transient(text: str) -> bool:
        low = text.lower()
        return any(marker in low for marker in _MCPDictAdapter._TRANSIENT_MARKERS)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        max_attempts = self._max_attempts
        base_backoff = self._base_backoff

        for attempt in range(max_attempts):
            is_last = attempt == max_attempts - 1
            backoff = min(base_backoff * (2 ** attempt), self._MAX_BACKOFF)
            try:
                result = await self._raw.call_tool(name, arguments)
            except PhoenixToolError:
                # A PhoenixToolError raised intentionally (genuine error) must
                # never be swallowed by the transport-exception handler.
                raise
            except Exception:
                # Transport / timeout exception — transient by definition.
                if is_last:
                    raise
                await asyncio.sleep(backoff)
                continue

            # CallToolResult.content is list[TextContent | ImageContent | EmbeddedResource]
            content = getattr(result, "content", None) or []
            text = next(
                (t for item in content if (t := getattr(item, "text", None)) is not None),
                None,
            )

            # A tool error surfaces as isError=True.
            # If the error is TRANSIENT (5xx/timeout keywords) and we have retries
            # left, sleep and retry.  Otherwise — genuine 4xx miss or last attempt —
            # raise PhoenixToolError so callers (e.g. sweep probing tag absence) get
            # the signal they rely on.
            if getattr(result, "isError", False):
                error_text = text or f"{name} returned isError with no content"
                if not is_last and self._is_transient(error_text):
                    await asyncio.sleep(backoff)
                    continue
                raise PhoenixToolError(error_text)

            # ---- success path (unchanged) ----
            if text is None:
                return {}

            # Phoenix often prefixes JSON with a sentence (e.g. upsert-prompt:
            # `Successfully created prompt "X":\n{...}`). Isolate the JSON tail by
            # cutting from whichever of `{`/`[` appears EARLIEST — checking `{` first
            # would slice into the middle of a bare array response (list-prompts).
            payload = text
            starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
            if starts:
                payload = text[min(starts):]
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                # Some tools return naked strings ("Successfully added tag ..."). Wrap.
                return {"_raw_text": text}

            # Normalize array responses (e.g. list-prompts) to {"items": [...]}.
            if isinstance(parsed, list):
                return {"items": parsed}
            if not isinstance(parsed, dict):
                return {"_raw_value": parsed}
            return parsed

        # Unreachable — loop always returns or raises — but satisfies type checker.
        raise PhoenixToolError(f"{name} exhausted all {max_attempts} attempts")


@asynccontextmanager
async def phoenix_client_from_env() -> AsyncIterator[PhoenixClient]:
    """Yield a PhoenixClient connected to the live Phoenix endpoint from env."""
    api_key = _require_env("PHOENIX_API_KEY")
    base_url = _require_env("PHOENIX_COLLECTOR_ENDPOINT").rstrip("/")
    mcp_package = os.environ.get(
        "PHOENIX_MCP_PACKAGE", "@arizeai/phoenix-mcp@latest"
    )

    # MCP server invocation.
    # The phoenix-mcp CLI accepts:
    #   --baseUrl <url>   (required)
    #   --apiKey <jwt>    (Phoenix Cloud + Arize AX)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", mcp_package, "--baseUrl", base_url, "--apiKey", api_key],
    )

    # REST client — Bearer + legacy api_key header for compatibility.
    rest_headers = {
        "Authorization": f"Bearer {api_key}",
        "api_key": api_key,
    }

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async with httpx.AsyncClient(
                base_url=base_url,
                headers=rest_headers,
                timeout=30.0,
                # Retry transient connection failures (e.g. intermittent DNS
                # "Name or service not known") so a long multi-round live run
                # survives a blip mid-apoptosis instead of aborting.
                transport=httpx.AsyncHTTPTransport(retries=3),
            ) as rest:
                yield PhoenixClient(
                    mcp_session=_MCPDictAdapter(session),
                    rest=rest,
                    base_url=base_url,
                )
