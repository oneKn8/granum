"""Phoenix client — wraps both MCP tool calls AND REST endpoints.

This is the SOLE seam between Granum and Phoenix. All Phoenix tool names and
REST paths appear ONLY here; business logic talks to typed methods.

Retrofitted 2026-06-02 (Phase 1.10b) to the REAL Phoenix MCP schema captured in
`research/phoenix-mcp-schemas.md`. The Phase 1.3 version was authored against a
fictional schema (`body`/`tags` on upsert, `promptId`/`versionId` keys,
tag-aware `list-prompts`). Verified-live corrections:

- `upsert-prompt` takes `template` (we map `body`→`template`), no `tags` param;
  tags are applied AFTER via `add-prompt-version-tag`. It returns the **version**
  GlobalID under `id`.
- `add-prompt-version-tag` takes `prompt_version_id` + `name` (the tag).
- `list-prompts` has no name filter and returns no tags/versions — only names +
  prompt ids. Active-population resolution is therefore: list → client-side
  prefix filter → `get-prompt-version-by-tag(name, "production")` per prompt.
- Phoenix strips `/` from prompt names, so this client normalizes the logical
  `/` separator used by callers to `__` (the sole place that mapping lives).
- Apoptosis (Path B) tag removal is REST-only:
  `DELETE /v1/prompt_versions/{vid}/tags/{tag}` → 204.

`prompt_id` is the (normalized) prompt NAME — stable across generations and
accepted as `prompt_identifier` everywhere. `version_id` is the per-generation
Phoenix version GlobalID used for tagging/removal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

_log = logging.getLogger(__name__)

# Phoenix stores prompts under a GOOGLE/Gemini provider so its UI renders the
# right model. Generation itself runs through Granum's own Vertex client, so
# this is cosmetic metadata on the prompt registry entry.
_DEFAULT_PROVIDER = "GOOGLE"
_DEFAULT_MODEL = "gemini-3.1-pro-preview"


class PhoenixToolError(RuntimeError):
    """An MCP tool returned ``isError=True`` (e.g. 404 on a tag/prompt miss).

    The live :class:`~granum.tools.phoenix_session._MCPDictAdapter` raises this
    so callers can distinguish a genuine miss (treat as "no active version")
    from a malformed success.
    """


class _MCPSession(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


def _normalize_name(name: str) -> str:
    """Map the logical ``/`` separator callers use to Phoenix-safe ``__``.

    Phoenix silently strips ``/`` from prompt names (verified live), which would
    desync stored names from the names we look up. Doing the mapping in ONE place
    keeps stored names and prefix filters consistent without touching callers.
    """
    return name.replace("/", "__")


def _extract_template_text(template: Any) -> str:
    """Pull the body string back out of a Phoenix chat-wrapped template.

    `upsert-prompt` wraps a plain string into
    ``{"type":"chat","messages":[{"role":...,"content":[{"type":"text","text":...}]}]}``.
    Accepts a plain string too (defensive).
    """
    if isinstance(template, str):
        return template
    if isinstance(template, dict):
        parts: list[str] = []
        for msg in template.get("messages") or []:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for chunk in content:
                    if isinstance(chunk, dict) and chunk.get("type") == "text":
                        parts.append(chunk.get("text", ""))
        return "\n".join(p for p in parts if p)
    return ""


@dataclass(frozen=True)
class PromptVersion:
    prompt_id: str
    version_id: str
    tags: tuple[str, ...] = ()
    body: str = ""
    name: str = ""


@dataclass(frozen=True)
class TransferEdge:
    source_cell: str
    target_cell: str
    source_prompt_id: str
    target_prompt_id: str
    mean_score: float
    p_value: float


class PhoenixClient:
    """Typed wrapper over arize-phoenix MCP + REST.

    Args:
        mcp_session: An active MCP client session (stdio or SSE transport).
        rest: An httpx.AsyncClient configured with the Phoenix base URL.
        base_url: Phoenix base URL (e.g. "https://app.phoenix.arize.com/s/<space>").
        default_model: model_name stamped on new prompt registry entries (cosmetic).
    """

    def __init__(
        self,
        *,
        mcp_session: _MCPSession,
        rest: httpx.AsyncClient,
        base_url: str,
        default_model: str = _DEFAULT_MODEL,
    ) -> None:
        self._mcp = mcp_session
        self._rest = rest
        self._base_url = base_url.rstrip("/")
        self._model = default_model

    # === Prompts ===

    async def upsert_prompt(
        self, *, name: str, body: str, tags: tuple[str, ...] = ("experimental",)
    ) -> PromptVersion:
        """Create a prompt (or a new version of an existing name) and tag it.

        Real `upsert-prompt` takes ``template`` (not ``body``), has no ``tags``
        param, and returns the new VERSION id under ``id``. Tags are applied in a
        follow-up `add-prompt-version-tag` call per tag.
        """
        nm = _normalize_name(name)
        resp = await self._mcp.call_tool(
            "upsert-prompt",
            {
                "name": nm,
                "template": body,
                "model_provider": _DEFAULT_PROVIDER,
                "model_name": self._model,
                "temperature": 0.0,
            },
        )
        version_id = resp["id"]
        for tag in tags:
            await self._mcp.call_tool(
                "add-prompt-version-tag",
                {"prompt_version_id": version_id, "name": tag},
            )
        return PromptVersion(
            prompt_id=nm,
            version_id=version_id,
            tags=tuple(tags),
            body=body,
            name=nm,
        )

    async def add_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> tuple[str, ...]:
        """Add a tag to a prompt version via MCP, return the version's live tag set.

        `add-prompt-version-tag` is MOVE-SEMANTIC: re-tagging ``production`` onto a
        new version strips it from the prior champion — the atomic champion-swap
        primitive. ``prompt_id`` is accepted for the call-site contract but the
        real API keys only on ``version_id``.
        """
        await self._mcp.call_tool(
            "add-prompt-version-tag",
            {"prompt_version_id": version_id, "name": tag},
        )
        return await self._version_tags(version_id)

    async def remove_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> None:
        """Remove a tag via REST (MCP exposes no tag-removal).

        Returns silently on 204 OR 404 — 404 means the tag was already absent,
        which is fine for tombstone idempotency.
        """
        url = f"{self._base_url}/v1/prompt_versions/{version_id}/tags/{tag}"
        resp = await self._rest.delete(url)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    async def _version_tags(self, version_id: str) -> tuple[str, ...]:
        """Read a version's current tags via REST (`GET .../tags` → {"data":[...]})."""
        url = f"{self._base_url}/v1/prompt_versions/{version_id}/tags"
        resp = await self._rest.get(url)
        if resp.status_code != 200:
            return ()
        data = resp.json().get("data", [])
        out: list[str] = []
        for item in data:
            if isinstance(item, dict):
                nm = item.get("name")
                if nm:
                    out.append(nm)
            elif item:
                out.append(str(item))
        return tuple(out)

    async def tombstone(self, prompt_id: str, version_id: str) -> None:
        """Functional apoptosis — Path B.

        1. Remove 'production' tag via REST (no longer in active population).
        2. Add 'tombstoned' tag via MCP (selection queries filter on its presence).

        The version itself is immutable and remains — audit history preserved.
        """
        await self.remove_version_tag(prompt_id, version_id, "production")
        await self._mcp.call_tool(
            "add-prompt-version-tag",
            {"prompt_version_id": version_id, "name": "tombstoned"},
        )

    async def list_active_prompts(self, *, name_prefix: str) -> list[PromptVersion]:
        """Return the active (production, not tombstoned) population under a prefix.

        Real `list-prompts` has no name filter and returns no tags/versions, so:
          1. `list-prompts` → all prompts (≤100, no cursor; a warning is logged if
             the space ever hits the cap so coverage is never silently truncated).
          2. client-side prefix filter on the (normalized) name.
          3. `get-prompt-version-by-tag(name, "production")` → the champion version
             (404 → no champion → skip).
          4. drop any version that also carries the `tombstoned` tag.
        """
        prefix = _normalize_name(name_prefix)
        resp = await self._mcp.call_tool("list-prompts", {"limit": 100})
        items = resp.get("items") or resp.get("prompts") or []
        if len(items) >= 100:
            _log.warning(
                "list-prompts returned %d (cap 100, no cursor) — population may be "
                "truncated for prefix %r", len(items), prefix,
            )
        result: list[PromptVersion] = []
        for p in items:
            nm = p.get("name", "")
            if not nm.startswith(prefix):
                continue
            try:
                ver = await self._mcp.call_tool(
                    "get-prompt-version-by-tag",
                    {"prompt_identifier": nm, "tag_name": "production"},
                )
            except PhoenixToolError:
                continue  # no production champion (extinct/tombstoned lineage)
            version_id = ver.get("id")
            if not version_id:
                continue
            tags = await self._version_tags(version_id)
            if "tombstoned" in tags:
                continue
            result.append(
                PromptVersion(
                    prompt_id=nm,
                    version_id=version_id,
                    # resolved via the production tag, so it's present even if the
                    # REST tag read came back thin.
                    tags=tags or ("production",),
                    body=_extract_template_text(ver.get("template")),
                    name=nm,
                )
            )
        return result

    async def list_all_prompts(self) -> list[dict[str, Any]]:
        """Return the raw prompt list (name + prompt id), tags/versions NOT included.

        Used by demo-setup/reset tooling that needs every prompt (incl. tombstoned),
        not just the active population.
        """
        resp = await self._mcp.call_tool("list-prompts", {"limit": 100})
        return resp.get("items") or resp.get("prompts") or []

    async def delete_prompt(self, prompt_id: str) -> None:
        """Hard-delete a prompt (and all its versions) via REST.

        This is a DEMO-SETUP / reset primitive, NOT apoptosis — apoptosis is
        tag-based and preserves audit history (:meth:`tombstone`). Hard delete is
        only for wiping a cell to a clean seed state between evolution runs.
        Tolerates 404 (already gone).
        """
        resp = await self._rest.delete(f"{self._base_url}/v1/prompts/{prompt_id}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    async def list_coevolution_state(
        self, *, cell: str
    ) -> tuple[list[PromptVersion], list[PromptVersion]]:
        """Return (writers, payers) — both active populations for a co-evolving cell.

        Writers live under ``{cell}/`` (→ ``{cell}__``), payers under
        ``{cell}_payer/`` (→ ``{cell}_payer__``). The normalized prefixes don't
        collide: the char after ``{cell}_`` is ``_`` for writers vs ``p`` for payers.
        """
        writers = await self.list_active_prompts(name_prefix=f"{cell}/")
        payers = await self.list_active_prompts(name_prefix=f"{cell}_payer/")
        return writers, payers

    # === Datasets ===

    @staticmethod
    def _as_example(row: dict[str, Any]) -> dict[str, Any]:
        """Coerce a flat analytics row into Phoenix's required {input,output,metadata}.

        Pass-through if already shaped; otherwise the whole row becomes ``output``
        (with empty ``input``) so the writeback is schema-valid.
        """
        if "input" in row and "output" in row:
            return {
                "input": row["input"],
                "output": row["output"],
                "metadata": row.get("metadata", {}),
            }
        meta = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
        return {"input": {}, "output": dict(row), "metadata": meta}

    async def add_dataset_examples(
        self, *, dataset_name: str, examples: list[dict[str, Any]]
    ) -> None:
        """Append outcome examples to a Phoenix dataset (antigen writeback).

        NOTE: there is no MCP `create-dataset` — the dataset must pre-exist. Cycle
        step-7 writeback wraps this call best-effort so a missing dataset never
        aborts the evolution core (see `cycle.py`).
        """
        await self._mcp.call_tool(
            "add-dataset-examples",
            {
                "dataset_name": dataset_name,
                "examples": [self._as_example(e) for e in examples],
            },
        )

    async def add_coevolution_example(
        self,
        *,
        cell: str,
        round_index: int,
        writer_id: str,
        payer_id: str,
        defensibility_composite: float,
        english_feedback: str,
    ) -> None:
        """Writeback one co-evolution round outcome to ``granum/{cell}/coevolution``."""
        await self.add_dataset_examples(
            dataset_name=f"granum/{cell}/coevolution",
            examples=[
                {
                    "round_index": round_index,
                    "writer_winner_id": writer_id,
                    "payer_winner_id": payer_id,
                    "defensibility_composite": defensibility_composite,
                    "english_feedback": english_feedback,
                }
            ],
        )

    async def add_transfer_edge(
        self,
        *,
        source_cell: str,
        target_cell: str,
        source_prompt_id: str,
        target_prompt_id: str,
        mean_score: float,
        p_value: float,
    ) -> None:
        """Write one accepted cross-cell transfer event to ``granum/transfer_edges``."""
        await self.add_dataset_examples(
            dataset_name="granum/transfer_edges",
            examples=[
                {
                    "source_cell": source_cell,
                    "target_cell": target_cell,
                    "source_prompt_id": source_prompt_id,
                    "target_prompt_id": target_prompt_id,
                    "mean_score": mean_score,
                    "p_value": p_value,
                }
            ],
        )

    async def list_transfer_edges(
        self, *, cell: str | None = None
    ) -> list[TransferEdge]:
        """Read accepted transfer edges, optionally filtered by either endpoint cell.

        Rows are stored as Phoenix examples (`{input, output, metadata}`); the edge
        payload lives in ``output``. Reads ``row["output"]`` then falls back to the
        bare row (defensive against pre-wrap rows).
        """
        resp = await self._mcp.call_tool(
            "get-dataset-examples",
            {"dataset_name": "granum/transfer_edges"},
        )
        rows = resp.get("examples") or resp.get("items") or []
        edges: list[TransferEdge] = []
        for raw in rows:
            row = raw.get("output", raw) if isinstance(raw, dict) else raw
            edges.append(
                TransferEdge(
                    source_cell=row["source_cell"],
                    target_cell=row["target_cell"],
                    source_prompt_id=row["source_prompt_id"],
                    target_prompt_id=row["target_prompt_id"],
                    mean_score=float(row["mean_score"]),
                    p_value=float(row["p_value"]),
                )
            )
        if cell is None:
            return edges
        return [e for e in edges if e.source_cell == cell or e.target_cell == cell]

    # === Spans / traces ===

    async def get_spans(
        self, *, project_name: str, filter_str: str = ""
    ) -> list[dict[str, Any]]:
        """Online introspection of recent spans for a project.

        Real `get-spans` keys on ``project_identifier`` and has no generic filter
        string (``filter_str`` is accepted for the call contract but ignored —
        use ``names``/``span_kinds`` server-side filters in a later iteration).
        """
        resp = await self._mcp.call_tool(
            "get-spans",
            {"project_identifier": project_name},
        )
        return resp.get("items") or resp.get("spans") or []
