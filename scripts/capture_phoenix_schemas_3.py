"""Probe #3 — the last two cycle-critical unknowns (Phase 1.10b).

  1. get-prompt-version-by-tag SUCCESS envelope (fields + version id + template)
  2. get-prompt-version-by-tag MISS behaviour (error vs empty) for an absent tag
  3. raw list-prompts (probe #2 printed empty — capture raw to see why)

Usage:
    cd granum/
    set -a; source .env; set +a
    source ~/.nvm/nvm.sh && nvm use default
    env -u PYTHONPATH uv run python scripts/capture_phoenix_schemas_3.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _texts(result: Any) -> list[str]:
    return [
        t for item in (getattr(result, "content", None) or [])
        if (t := getattr(item, "text", None)) is not None
    ]


def _show(label: str, result: Any) -> None:
    print(f"\n----- {label} -----")
    print(f"isError={getattr(result, 'isError', None)}")
    for i, t in enumerate(_texts(result)):
        print(f"[content[{i}].text]\n{t}")


async def _amain() -> int:
    api_key = os.environ.get("PHOENIX_API_KEY")
    base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").rstrip("/")
    if not api_key or not base_url:
        print("ERROR: env not set", file=sys.stderr)
        return 2

    mcp_package = os.environ.get("PHOENIX_MCP_PACKAGE", "@arizeai/phoenix-mcp@latest")
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", mcp_package, "--baseUrl", base_url, "--apiKey", api_key],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Raw list-prompts.
            r = await session.call_tool("list-prompts", {})
            _show("list-prompts RAW", r)

            # Create a fresh, slash-free prompt and tag it production.
            name = "granumprobe_resolve"
            r = await session.call_tool(
                "upsert-prompt",
                {"name": name, "template": "resolve probe {x}",
                 "model_provider": "GOOGLE", "model_name": "gemini-3.1-pro-preview"},
            )
            version_id = None
            for t in _texts(r):
                idx = t.find("{")
                if idx != -1:
                    try:
                        version_id = json.loads(t[idx:]).get("id")
                    except json.JSONDecodeError:
                        pass
            print(f"\n[fresh prompt version_id] {version_id!r}")

            if version_id:
                await session.call_tool(
                    "add-prompt-version-tag",
                    {"prompt_version_id": version_id, "name": "production"},
                )

            # 1. SUCCESS resolution
            r = await session.call_tool(
                "get-prompt-version-by-tag",
                {"prompt_identifier": name, "tag_name": "production"},
            )
            _show("get-prompt-version-by-tag(production) SUCCESS", r)

            # 2. MISS resolution (tag never applied)
            r = await session.call_tool(
                "get-prompt-version-by-tag",
                {"prompt_identifier": name, "tag_name": "tombstoned"},
            )
            _show("get-prompt-version-by-tag(tombstoned) MISS", r)

            # 3. MISS on absent prompt
            r = await session.call_tool(
                "get-prompt-version-by-tag",
                {"prompt_identifier": "granumprobe_does_not_exist", "tag_name": "production"},
            )
            _show("get-prompt-version-by-tag(absent prompt) MISS", r)

    return 0


def main() -> int:
    import asyncio
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
