# Phoenix MCP Capability Audit (Pre-flight Task A)

**Date:** 2026-05-27
**Purpose:** Empirically verify what Phoenix supports for the Granum "functional apoptosis" mechanism before Phase 0 begins. Locks the implementation path.
**Conducted by:** Granum pre-flight audit subagent
**Environment:** Local Docker (`arizephoenix/phoenix:latest`) + `@arizeai/phoenix-mcp@latest` over stdio JSON-RPC + direct REST probes.

---

## 1. Versions Tested

| Component | Version | Source |
|---|---|---|
| Phoenix server (Docker image) | **16.3.0** | `docker exec phoenix-audit python -c "import phoenix; print(phoenix.__version__)"` → `16.3.0`; image label `version-16.3.0-root`, revision `06da8eb5f6db02c1c5286f005e6690971b7c4227` |
| Phoenix `@arizeai/phoenix-mcp` npm package | **4.0.13** | `npm view @arizeai/phoenix-mcp version` |
| MCP server protocol | **2024-11-05** | from `initialize` response |
| MCP serverInfo name/version | `phoenix-mcp-server` / **1.1.0** | from `initialize` response |
| OpenAPI spec served at | `http://localhost:6006/openapi.json` | 205,370 bytes |

Image digest: `sha256:91bb10c1217cd1fc0b3ac5908cc8d11f663bc56e00241b7f7551af880d5bcd92`.

---

## 2. MCP Tool Inventory (27 tools)

Source: `tools/list` over stdio JSON-RPC after `initialize` + `notifications/initialized`.

### Prompts (10)
| Tool | Mutates? | Purpose |
|---|---|---|
| `list-prompts` | no | List all prompts (pagination only, **no tag filter**) |
| `get-prompt` | no | Generic MCP-native prompt fetch |
| `get-latest-prompt` | no | Latest version of a prompt |
| `get-prompt-by-identifier` | no | Latest version by name or ID |
| `get-prompt-version` | no | Specific version by version ID |
| `get-prompt-version-by-tag` | no | Resolve a tag name to its current version |
| `list-prompt-versions` | no | All versions of a prompt (pagination only) |
| `list-prompt-version-tags` | no | All tags on a given version |
| `upsert-prompt` | yes | Create prompt + initial version, **or** create new version of existing prompt (no separate "create version" tool) |
| `add-prompt-version-tag` | yes | Attach tag to a version. **Side effect: silently moves tag if name already exists elsewhere.** Returns 204. |

### Datasets (7)
`list-datasets`, `get-dataset`, `get-dataset-examples`, `get-dataset-experiments`, `add-dataset-examples`, `list-experiments-for-dataset`, `get-experiment-by-id`.

### Tracing (8)
`list-projects`, `get-project`, `list-traces`, `get-trace`, `get-spans`, `get-span-annotations`, `list-sessions`, `get-session`.

### Misc (2)
`list-annotation-configs`, `phoenix-support`.

### Conspicuously absent from MCP (verified)
- No `delete-prompt`
- No `delete-prompt-version`
- No `remove-prompt-version-tag`
- No `delete-dataset` / `delete-example`
- No span-mutation tools (POSTing spans is OTLP/REST only)
- No `set-experiment-result` or eval-recording mutator

**Implication:** MCP is read-mostly + prompt versioning + tag promotion. All deletion + tag removal flow through REST.

---

## 3. REST API Capability (`/openapi.json`)

Endpoints that matter for Granum apoptosis (paths grepped for `prompt|dataset|trace|span`):

| Path | Methods | Notes |
|---|---|---|
| `/v1/prompts` | GET, POST | POST = upsert-prompt |
| `/v1/prompts/{id}` | **DELETE**, GET | **Whole-prompt cascade delete works (204)** |
| `/v1/prompts/{id}/versions` | GET | No filter; pagination only |
| `/v1/prompts/{id}/latest` | GET | |
| `/v1/prompts/{id}/tags/{tag}` | GET | Resolve tag → version |
| `/v1/prompt_versions/{vid}` | GET only | **No DELETE — 405 Method Not Allowed** |
| `/v1/prompt_versions/{vid}/tags` | GET, POST | POST adds/moves tag |
| `/v1/prompt_versions/{vid}/tags/{tag}` | **DELETE**, GET | **Remove tag from version (204)** — exists in REST, NOT in MCP |
| `/v1/datasets`, `/v1/datasets/{id}` | GET / DELETE+GET | Dataset cascade delete supported |
| `/v1/datasets/upload` | POST | Sync via `?sync=true`; supports `action: create | append` (versioned) |
| `/v1/datasets/{id}/versions` | GET | Datasets are append-versioned |
| `/v1/projects/{id}/spans` | GET, POST | Filter by `trace_id, parent_id, name, span_kind, status_code, attribute, start_time, end_time` |
| `/v1/projects/{id}/traces` | GET | |
| `/v1/spans/{id}`, `/v1/traces/{id}` | DELETE | Individual span/trace delete |
| `/v1/span_annotations`, `/v1/trace_annotations` | POST + DELETE | For writing eval annotations |

---

## 4. Capability Matrix (empirical, with evidence)

| # | Operation | MCP | REST | Verdict | Evidence |
|---|---|---|---|---|---|
| 4a | Create new prompt + v1 | `upsert-prompt` ✅ | `POST /v1/prompts` ✅ | Works | HTTP 200, returns `prompt_version_id` (note: response payload only contains the version object, not the parent prompt id — must `GET /v1/prompts` to get prompt id) |
| 4b | Create new version of existing prompt | `upsert-prompt` (same tool, idempotent on name) ✅ | `POST /v1/prompts` ✅ | Works | v2 added; `list-prompt-versions` returns both |
| 4c | Add tag `production` to v1 | `add-prompt-version-tag` ✅ | `POST /v1/prompt_versions/{v1}/tags` ✅ | Works | HTTP 204 |
| 4d | Add `production` to v2 while v1 has it | ✅ | ✅ | **Silently moves** | HTTP 204; afterwards v1 tag list = `[]`, v2 tag list = `[production]`. Confirmed via both REST and MCP. |
| 4e | Resolve `production` → version | `get-prompt-version-by-tag` ✅ | `GET /v1/prompts/{name}/tags/production` ✅ | Works | Returns v2 |
| 4f | Remove tag from version | ❌ **Not in MCP** | `DELETE /v1/prompt_versions/{v}/tags/{tag}` ✅ | **REST-only** | HTTP 204; subsequent `GET .../tags/{tag}` returns 404 |
| 4g | Delete single prompt version | ❌ Not in MCP | `DELETE /v1/prompt_versions/{vid}` ❌ | **NOT POSSIBLE** | HTTP **405 Method Not Allowed**. Versions are immutable as documentation states. |
| 4h | Delete whole prompt | ❌ Not in MCP | `DELETE /v1/prompts/{id}` ✅ | Works (cascade) | HTTP 204; `list-prompts` empties; all versions + tags gone |
| 4i | Tombstone via tag (e.g. add `tombstoned`) | ✅ via `add-prompt-version-tag` | ✅ | Works | HTTP 204, tag resolves correctly |
| 4j | `list-prompts` filtered by tag presence/absence | ❌ | ❌ | **Client-side filter required** | `list-prompts` params: only `cursor`, `limit` |
| 5a | Create dataset | n/a (no MCP create-dataset) | `POST /v1/datasets/upload?sync=true` ✅ | Works | HTTP 200; returns `dataset_id` + `version_id` |
| 5b | Append rows to dataset | `add-dataset-examples` ✅ | `POST /v1/datasets/upload` w/ `action:"append"` ✅ | Works | HTTP 200; produces **new dataset version** |
| 5c | List dataset versions | n/a | `GET /v1/datasets/{id}/versions` ✅ | Works | Verified 2 versions after one append |
| 5d | Query dataset by metadata | indirect (via `get-dataset-examples` then filter) | `GET /v1/datasets/{id}/examples` returns metadata inline ✅ | Works (client-side filter) | No server-side metadata filter parameter |
| 5e | Cross-experiment dataset reuse | Yes — experiments key off `dataset_id` + `version_id` | Yes | Works | `list-experiments-for-dataset` returns all experiments per dataset |
| 6a | List traces with filter | `list-traces` (project only) | `GET /v1/projects/{id}/traces` | Limited | Only project-level filter via path; no attribute filter on traces list |
| 6b | Get spans with rich filter | `get-spans` ✅ | `GET /v1/projects/{id}/spans` ✅ | Works | Filter params: `trace_id, parent_id, name, span_kind, status_code, attribute, start_time, end_time, cursor, limit` |
| 6c | Get trace with annotations | `get-trace` + `get-span-annotations` | `GET /v1/projects/{id}/traces` + `GET /v1/projects/{id}/span_annotations` | Two-step | No single endpoint joins them |
| 6d | Recency window: POST span → queryable | n/a (POST is REST/OTLP only) | `POST /v1/projects/{id}/spans` (202) → readable in ≤2s | Effectively real-time | Span POSTed with `attributes: {granum.strategy, granum.outcome}` was retrievable via GET 2 seconds later, with attributes preserved verbatim |

### Key surprises that change the plan
1. **`add-prompt-version-tag` is destructive/move-style, not append-style.** This is exactly the primitive needed for promote/demote, but it means there is no concept of "two versions both tagged `production`" — the tag is unique per prompt. Granum can use this directly for `champion` tag promotion: re-tag v_new with `champion` and v_old loses it atomically.
2. **No `remove-prompt-version-tag` MCP tool.** Granum's PhoenixClient must speak REST directly for tombstoning removal (or for un-tombstoning, if needed).
3. **Prompt-version deletion is impossible (405).** This is the load-bearing constraint the plan critics flagged — empirically confirmed. Path A (hard deletion of losers) is OFF THE TABLE.
4. **Whole-prompt deletion DOES work (cascade).** Path C's worst-case framing ("whole-prompt deletion as nuclear option") is real, but it destroys audit history. We must NOT use it for apoptosis — only for test cleanup.
5. **`list-prompts` has zero filter capability.** Apoptosis filtering must happen client-side after `list-prompt-versions` + `list-prompt-version-tags` per version. For populations of ≤20 strategies this is fine. For 1000s it would need rethinking, but Granum's design caps the active population.
6. **Span attributes survive round-trip verbatim and are queryable.** `attribute` query param on `/spans` enables retrieval like `attribute=granum.strategy:polite_legalistic`. This is the substrate for the bandit selector's reward signal.

---

## 5. Apoptosis Path Decision: **Path B (functional apoptosis via tag manipulation)**

### Rationale
- **Path A (hard version-level deletion)** is empirically refuted: `DELETE /v1/prompt_versions/{vid}` → HTTP 405 Method Not Allowed. Versions are immutable. The critics were right.
- **Path C (whole-prompt deletion)** is technically supported but destroys all evolutionary history — antithetical to the "immune system memory" thesis Granum is selling. Reserve for test fixture cleanup only.
- **Path B (tag-based tombstoning)** is the only path that (a) preserves audit history, (b) is fully supported, and (c) maps cleanly to the biology metaphor — apoptosis is *programmed cell death with phagocytic cleanup*, not erasure. The cell's memory persists in the immune system's records (Phoenix DB) even after it's removed from the active population.

### Path B implementation contract
1. Each Phoenix prompt version represents one Granum **strategy**.
2. Active population = `{v : v has tag "active" AND v does NOT have tag "tombstoned"}`. Filter happens in `PhoenixClient.list_active_strategies()` because the API has no server-side filter.
3. **Birth** (new strategy): `upsert-prompt` → version created → `add-prompt-version-tag(v, "active")`.
4. **Promotion** (champion): `add-prompt-version-tag(v_winner, "champion")` — automatically demotes prior champion (silent-move semantics).
5. **Apoptosis** (loser eliminated by bandit): two REST calls because MCP doesn't expose tag removal — (a) `DELETE /v1/prompt_versions/{v}/tags/active`, (b) `POST /v1/prompt_versions/{v}/tags` with `{name: "tombstoned"}`. Wrap in a `tombstone(v)` method with retry + idempotency check (calling DELETE on already-absent tag returns 404 — treat as success).
6. **Resurrection** (rare; if a tombstoned strategy beats current champion in shadow eval): inverse of step 5.
7. **NEVER call** `DELETE /v1/prompts/{id}` in production code — only in `tests/conftest.py` teardown.

### What Granum must build in the PhoenixClient layer
- A thin REST wrapper for the four tag-mutating endpoints (MCP can't be trusted for tag removal).
- Client-side filtering for `list_active_strategies()` because the server can't.
- An idempotent `tombstone(version_id)` that tolerates a missing `active` tag.
- Strict assertion in the Granum agent that it NEVER calls `delete_prompt(prompt_id)` outside test code (linter rule + runtime guard).

---

## 6. Recommended `PhoenixClient` interface stubs (for next subagent)

```python
# granum/infra/phoenix_client.py — to be implemented in Phase 0.4

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional

@dataclass(frozen=True)
class PromptVersion:
    prompt_id: str          # base64 GlobalID, e.g. "UHJvbXB0OjE="
    prompt_name: str
    version_id: str         # base64 GlobalID, e.g. "UHJvbXB0VmVyc2lvbjox"
    description: str
    template: dict          # raw Phoenix template payload
    tags: tuple[str, ...]   # ordered, lowercase

class PhoenixClient:
    """
    Granum's Phoenix integration. Hybrid: MCP for read + write-version + tag-add,
    REST for tag-removal + dataset upload + prompt-id resolution + cascade-delete (tests only).

    Apoptosis contract: tombstone() and resurrect() are the ONLY mutators called
    by the bandit selector. delete_prompt() is reserved for test teardown.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None: ...

    # ---- prompt / version ----
    def upsert_strategy(self, name: str, template: dict, *, description: str = "", model: str = "gpt-4o-mini") -> PromptVersion:
        """Create prompt if absent, OR add a new version to existing prompt. Tag new version with 'active'."""

    def get_latest_version(self, name: str) -> PromptVersion: ...

    def list_versions(self, name: str) -> list[PromptVersion]: ...

    def get_version_by_tag(self, name: str, tag: str) -> Optional[PromptVersion]: ...

    # ---- selection ----
    def list_active_strategies(self) -> list[PromptVersion]:
        """Active = has 'active' tag AND lacks 'tombstoned' tag. Filtered client-side."""

    def list_tombstoned_strategies(self) -> list[PromptVersion]: ...

    # ---- mutation: tags (the apoptosis primitives) ----
    def add_tag(self, version_id: str, tag: str, description: str = "") -> None:
        """Idempotent; silently moves tag if it exists on another version of the same prompt."""

    def remove_tag(self, version_id: str, tag: str) -> None:
        """REST-only (MCP doesn't expose). 404 → treat as success."""

    def promote_champion(self, version_id: str) -> None:
        """Equivalent to add_tag(version_id, 'champion'). Demotes prior champion atomically."""

    def tombstone(self, version_id: str) -> None:
        """Apoptosis. remove_tag('active') then add_tag('tombstoned'). Idempotent."""

    def resurrect(self, version_id: str) -> None:
        """Inverse of tombstone. Used only if a tombstoned strategy wins a shadow eval."""

    # ---- datasets ----
    def upsert_dataset(self, name: str, examples: Iterable[dict]) -> str:
        """Returns dataset_id. Uses action=create on first call, action=append after."""

    def list_dataset_versions(self, dataset_id: str) -> list[dict]: ...

    # ---- traces / spans ----
    def log_appeal_span(self, *, trace_id: str, strategy_version_id: str, outcome: str, attrs: dict) -> None:
        """POST span via REST. Attributes prefixed with 'granum.' for queryability."""

    def query_spans_by_strategy(self, strategy_version_id: str, since: Optional[str] = None) -> list[dict]:
        """GET /v1/projects/default/spans?attribute=granum.strategy_version_id:<id>"""

    # ---- DANGER: test-only ----
    def _delete_prompt_cascade(self, prompt_id: str) -> None:
        """DELETE /v1/prompts/{id}. Drops ALL versions + tags. Forbidden in production code paths."""
```

### Notes for the implementer
- Use `httpx.AsyncClient` for REST; keep MCP optional (for the demo / agent surface) but make the REST path canonical for mutations.
- Always pass `?sync=true` on dataset upload — async mode returns no `dataset_id`.
- When parsing list responses, every Phoenix resource ID is a base64-encoded GlobalID (e.g. `UHJvbXB0VmVyc2lvbjox` = `PromptVersion:1`). Treat them as opaque strings.
- `upsert_strategy()` returns the version object but Phoenix's POST response **does not include the parent prompt_id**; an extra `GET /v1/prompts` may be required for first-time creation if the caller needs the prompt_id.
- Add a `runtime_guard.py` that raises if `_delete_prompt_cascade` is called outside `tests/`.

---

## 7. Test artifacts retained for reproducibility

Local files (`/tmp/phoenix-audit/`, NOT committed):
- `tools_raw.json` — full `tools/list` MCP response
- `tools_list.tsv` — one-line summary per MCP tool
- `openapi.json` — Phoenix REST OpenAPI spec (205 KB)
- `p1.json`, `p2.json` — prompt creation responses
- `tag1.json`, `tag2.json`, `del_tag.json` — tag operation responses
- `delv.json`, `delp.json` — version-delete (405) and prompt-delete (204) probes
- `ds.json`, `ds_append.json` — dataset upload responses
- `span_post.json` — span POST response

Phoenix container: `docker rm -f phoenix-audit` to clean up.

---

## 8. Decision summary (for the master plan)

> **LOCKED: Path B — Functional apoptosis via tag manipulation.**
>
> Granum implements apoptosis as the atomic two-step (`remove_tag('active')` + `add_tag('tombstoned')`) at the prompt-version level, via REST. Audit history is preserved on every Phoenix prompt forever. The "immune system memory" framing in the submission is literally true: every losing strategy stays in the database with its full trace history, tombstoned but never erased.
>
> Hard deletion (Path A) is empirically impossible. Whole-prompt deletion (Path C) is reserved for test teardown only.
