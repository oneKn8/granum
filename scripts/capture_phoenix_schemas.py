"""Capture the REAL Phoenix MCP tool schemas + response envelopes (Phase 1.10b).

The 2026-05-27 audit (research/phoenix-mcp-audit.md) captured tool *names* and
*descriptions* but NOT per-tool inputSchema or response shapes. That gap made
PhoenixClient (Phase 1.3) wrong against the live MCP. This script closes it:

1. `session.list_tools()` → dump every tool's name + description + inputSchema.
2. Targeted live invocations of the prompt tools that drive the germinal loop,
   printing the RAW `content[*].text` so the text-prefix envelope is visible.

Read-mostly: the only writes are one throwaway probe prompt + a tag on it, in a
clearly-named `granumprobe...` namespace that never collides with real cells.

Usage:
    cd granum/
    set -a; source .env; set +a
    source ~/.nvm/nvm.sh && nvm use default   # npx on PATH for @arizeai/phoenix-mcp
    env -u PYTHONPATH uv run python scripts/capture_phoenix_schemas.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Tools whose request schema AND response envelope we care about most (the
# germinal-loop core). We still dump inputSchema for ALL tools, but only these
# get a live round-trip.
PROMPT_TOOLS_OF_INTEREST = [
    "list-prompts",
    "upsert-prompt",
    "add-prompt-version-tag",
    "get-latest-prompt",
]


def _raw_texts(result: Any) -> list[str]:
    """Return the raw text of every text content block in a CallToolResult."""
    out: list[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text is not None:
            out.append(text)
    return out


def _show_result(label: str, result: Any) -> None:
    print(f"\n----- {label} -----")
    print(f"isError={getattr(result, 'isError', None)}")
    texts = _raw_texts(result)
    if not texts:
        print("(no text content)")
        return
    for i, t in enumerate(texts):
        print(f"[content[{i}].text RAW]\n{t}")
        # Try to parse so we can report the real keys/shape.
        body = t
        # Phoenix often prefixes JSON with a sentence; isolate the JSON tail.
        for marker in ("{", "["):
            idx = t.find(marker)
            if idx != -1:
                body = t[idx:]
                break
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            print("[parse] not JSON after prefix-strip")
            continue
        if isinstance(parsed, dict):
            print(f"[parse] dict keys = {sorted(parsed.keys())}")
        elif isinstance(parsed, list):
            print(f"[parse] list len = {len(parsed)}")
            if parsed and isinstance(parsed[0], dict):
                print(f"[parse] item[0] keys = {sorted(parsed[0].keys())}")


async def _amain() -> int:
    api_key = os.environ.get("PHOENIX_API_KEY")
    base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").rstrip("/")
    if not api_key or not base_url:
        print("ERROR: PHOENIX_API_KEY / PHOENIX_COLLECTOR_ENDPOINT not set", file=sys.stderr)
        return 2

    mcp_package = os.environ.get("PHOENIX_MCP_PACKAGE", "@arizeai/phoenix-mcp@latest")
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", mcp_package, "--baseUrl", base_url, "--apiKey", api_key],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # === 1. Full tool inventory with inputSchema ===
            tools_result = await session.list_tools()
            tools = tools_result.tools
            print("=" * 70)
            print(f"TOOL INVENTORY — {len(tools)} tools")
            print("=" * 70)
            for tool in sorted(tools, key=lambda t: t.name):
                print(f"\n### {tool.name}")
                desc = (tool.description or "").strip().splitlines()
                print(f"desc: {desc[0] if desc else ''}")
                schema = tool.inputSchema or {}
                print("inputSchema:")
                print(json.dumps(schema, indent=2, sort_keys=True))

            print("\n" + "=" * 70)
            print("LIVE RESPONSE ENVELOPES (prompt-tool round-trip)")
            print("=" * 70)

            tool_names = {t.name for t in tools}

            # === 2a. list-prompts (read-only) ===
            if "list-prompts" in tool_names:
                try:
                    r = await session.call_tool("list-prompts", {})
                    _show_result("list-prompts (no args)", r)
                except Exception as exc:  # noqa: BLE001
                    print(f"\nlist-prompts no-arg FAILED: {exc}")

            # === 2b. upsert-prompt (one throwaway probe) ===
            probe_name = "granumprobe_schema_check"
            probe_id: str | None = None
            probe_version_id: str | None = None
            if "upsert-prompt" in tool_names:
                # Try the schema-correct shape first: template (not body), no tags.
                for args in (
                    {"name": probe_name, "template": "Probe template for schema capture. {placeholder}"},
                    {"name": probe_name, "description": "schema probe",
                     "template": "Probe template for schema capture. {placeholder}"},
                ):
                    try:
                        r = await session.call_tool("upsert-prompt", args)
                        _show_result(f"upsert-prompt args={sorted(args.keys())}", r)
                        if not getattr(r, "isError", False):
                            # Pull id/version out of the first JSON blob.
                            for t in _raw_texts(r):
                                idx = t.find("{")
                                if idx == -1:
                                    continue
                                try:
                                    obj = json.loads(t[idx:])
                                except json.JSONDecodeError:
                                    continue
                                probe_id = obj.get("id") or obj.get("promptId") or probe_id
                                # version id may be nested or separate
                                probe_version_id = (
                                    obj.get("version_id")
                                    or obj.get("versionId")
                                    or (obj.get("version") or {}).get("id")
                                    if isinstance(obj.get("version"), dict)
                                    else obj.get("version_id") or obj.get("versionId")
                                ) or probe_version_id
                            break
                    except Exception as exc:  # noqa: BLE001
                        print(f"\nupsert-prompt args={sorted(args.keys())} FAILED: {exc}")

            print(f"\n[probe captured] id={probe_id!r} version_id={probe_version_id!r}")

            # === 2c. get-latest-prompt for the probe (read) ===
            if "get-latest-prompt" in tool_names:
                for args in (
                    {"prompt_identifier": probe_name},
                    {"promptName": probe_name},
                    {"name": probe_name},
                ):
                    try:
                        r = await session.call_tool("get-latest-prompt", args)
                        _show_result(f"get-latest-prompt args={sorted(args.keys())}", r)
                        if not getattr(r, "isError", False):
                            break
                    except Exception as exc:  # noqa: BLE001
                        print(f"\nget-latest-prompt args={sorted(args.keys())} FAILED: {exc}")

            # === 2d. add-prompt-version-tag on the probe ===
            if "add-prompt-version-tag" in tool_names and probe_version_id:
                for args in (
                    {"prompt_version_id": probe_version_id, "name": "experimental"},
                    {"promptVersionId": probe_version_id, "name": "experimental"},
                    {"version_id": probe_version_id, "tag": "experimental"},
                ):
                    try:
                        r = await session.call_tool("add-prompt-version-tag", args)
                        _show_result(f"add-prompt-version-tag args={sorted(args.keys())}", r)
                        if not getattr(r, "isError", False):
                            break
                    except Exception as exc:  # noqa: BLE001
                        print(f"\nadd-prompt-version-tag args={sorted(args.keys())} FAILED: {exc}")
            else:
                print("\n(skipping add-prompt-version-tag — no probe_version_id captured)")

            # === 2e. list-prompts again to see the probe in list shape ===
            if "list-prompts" in tool_names:
                try:
                    r = await session.call_tool("list-prompts", {})
                    _show_result("list-prompts (after probe upsert)", r)
                except Exception as exc:  # noqa: BLE001
                    print(f"\nlist-prompts (post) FAILED: {exc}")

    return 0


def main() -> int:
    import asyncio

    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
