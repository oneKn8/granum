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

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from granum.tools.phoenix_client import PhoenixClient


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Source .env or export it before running."
        )
    return value


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
            ) as rest:
                yield PhoenixClient(
                    mcp_session=session, rest=rest, base_url=base_url
                )
