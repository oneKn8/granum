"""Probe #2 — verify the operations the germinal CYCLE depends on (Phase 1.10b).

Probe #1 captured inputSchemas + upsert/list/get envelopes but skipped the
write-side chain. This nails, LIVE:
  1. slash-stripping behaviour on prompt names (decides the cell separator)
  2. add-prompt-version-tag round-trip (tag a known version 'production')
  3. get-prompt-version-by-tag resolution (tag -> version)
  4. REST tag-removal primitive (apoptosis Path B) + its status code
  5. get-prompt-version-by-tag after removal (confirm gone)

Usage:
    cd granum/
    set -a; source .env; set +a
    source ~/.nvm/nvm.sh && nvm use default
    env -u PYTHONPATH uv run python scripts/capture_phoenix_schemas_2.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx
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


def _json_tail(text: str) -> Any:
    for m in ("{", "["):
        idx = text.find(m)
        if idx != -1:
            try:
                return json.loads(text[idx:])
            except json.JSONDecodeError:
                return None
    return None


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

            # === 1. Slash-stripping test ===
            slash_name = "granumprobe/slash_test"
            r = await session.call_tool(
                "upsert-prompt",
                {"name": slash_name, "template": "slash probe {x}",
                 "model_provider": "GOOGLE", "model_name": "gemini-3.1-pro-preview"},
            )
            _show(f"upsert-prompt name={slash_name!r} provider=GOOGLE", r)
            slash_version_id = None
            for t in _texts(r):
                obj = _json_tail(t)
                if isinstance(obj, dict):
                    slash_version_id = obj.get("id")

            r = await session.call_tool("list-prompts", {})
            print("\n----- list-prompts: names actually stored -----")
            for t in _texts(r):
                obj = _json_tail(t)
                if isinstance(obj, list):
                    for p in obj:
                        print(f"  stored name={p.get('name')!r}  prompt_id={p.get('id')!r}")

            # === 2. Tag the slash-probe's version 'production' ===
            if slash_version_id:
                r = await session.call_tool(
                    "add-prompt-version-tag",
                    {"prompt_version_id": slash_version_id, "name": "production"},
                )
                _show(f"add-prompt-version-tag(version={slash_version_id}, name=production)", r)

            # === 3. Resolve tag -> version ===
            # prompt_identifier = whatever name got stored (compute below from list)
            r = await session.call_tool("list-prompts", {})
            stored_names = []
            for t in _texts(r):
                obj = _json_tail(t)
                if isinstance(obj, list):
                    stored_names = [p.get("name") for p in obj]
            # the slash-probe stored name is the one containing 'slash_test'
            slash_stored = next((n for n in stored_names if n and "slash_test" in n), None)
            print(f"\n[slash-probe stored as] {slash_stored!r}")

            if slash_stored:
                r = await session.call_tool(
                    "get-prompt-version-by-tag",
                    {"prompt_identifier": slash_stored, "tag_name": "production"},
                )
                _show("get-prompt-version-by-tag(production) BEFORE removal", r)

            # === 4. REST tag removal (apoptosis Path B) ===
            if slash_version_id:
                rest_headers = {"Authorization": f"Bearer {api_key}", "api_key": api_key}
                async with httpx.AsyncClient(base_url=base_url, headers=rest_headers, timeout=30.0) as rest:
                    for path in (
                        f"/v1/prompt_versions/{slash_version_id}/tags/production",
                    ):
                        try:
                            resp = await rest.delete(path)
                            print(f"\n[REST DELETE {path}] status={resp.status_code} body={resp.text[:300]!r}")
                        except Exception as exc:  # noqa: BLE001
                            print(f"\n[REST DELETE {path}] FAILED: {exc}")
                    # Also probe how tags are listed via REST (to learn the tag id/route).
                    try:
                        resp = await rest.get(f"/v1/prompt_versions/{slash_version_id}/tags")
                        print(f"\n[REST GET .../tags] status={resp.status_code} body={resp.text[:500]!r}")
                    except Exception as exc:  # noqa: BLE001
                        print(f"\n[REST GET .../tags] FAILED: {exc}")

            # === 5. Confirm tag gone via MCP ===
            if slash_stored:
                r = await session.call_tool(
                    "get-prompt-version-by-tag",
                    {"prompt_identifier": slash_stored, "tag_name": "production"},
                )
                _show("get-prompt-version-by-tag(production) AFTER removal", r)

    return 0


def main() -> int:
    import asyncio
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
