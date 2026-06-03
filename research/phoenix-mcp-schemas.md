# Phoenix MCP — Verified Tool Schemas & Response Envelopes (Phase 1.10b)

**Captured live:** 2026-06-02 against `https://app.phoenix.arize.com/s/shifatislamsanto764`
**MCP server:** `@arizeai/phoenix-mcp@latest` (stdio), 27 tools
**Capture scripts:** `scripts/capture_phoenix_schemas.py`, `_2.py`, `_3.py` (re-runnable)

> This document supersedes the schema guesses baked into the Phase 1.3 `PhoenixClient`.
> The 2026-05-27 audit (`research/phoenix-mcp-audit.md`) captured tool *names* and
> *descriptions* but NOT per-tool `inputSchema` or response shapes. That gap made the
> client wrong against the live MCP (see [[feedback-audit-schemas-not-just-names]]).
> Everything below is from real `list_tools()` + real round-trips, not documentation.

---

## The four+ mismatches that broke the Phase 1.3 client

| # | Phase 1.3 assumed | Reality (verified) |
|---|---|---|
| 1 | `upsert-prompt` takes `body` | takes **`template`** (required) |
| 2 | `upsert-prompt` takes `tags` | **no tags param** — tag *after* via `add-prompt-version-tag` |
| 3 | response keys `promptId` / `versionId` | text-prefixed JSON; key is **`id`** = the **version** GlobalID |
| 4 | names preserved | **`/` is stripped**: `a/b` → `ab`. Use `__` as separator |
| 5 | `list-prompts` supports `namePrefix` + returns `tags` | **only `limit`**; returns **no tags, no versions**; `id` = **prompt** GlobalID |
| 6 | `add-prompt-version-tag` args `promptId`/`versionId`/`tag` | **`prompt_version_id`** + **`name`** (the tag) |
| 7 | `add-dataset-examples` rows are flat dicts | rows are **`{input, output, metadata}`**, input+output required |

The deep one is #5: the whole `list_active_prompts(name_prefix=, filter-by-tags)` design
was incompatible with the real API. Real flow = `list-prompts` (client-side prefix filter)
→ `get-prompt-version-by-tag(name, "production")` per prompt to resolve the champion.

---

## Prompt tools (germinal-loop core)

### `upsert-prompt` — create prompt / add a version
```json
inputSchema: {
  "name":           {"type": "string"},                        // required
  "template":       {"type": "string"},                        // required
  "description":    {"type": "string"},
  "model_name":     {"type": "string", "default": "gpt-4"},
  "model_provider": {"enum": ["OPENAI","AZURE_OPENAI","ANTHROPIC","GOOGLE"], "default": "OPENAI"},
  "temperature":    {"type": "number", "default": 0.7}
}
```
**Response** (text-prefixed — the `_MCPDictAdapter` must strip the prefix before JSON):
```
Successfully created prompt "granumprobe_schema_check":
{ "description":"", "model_provider":"GOOGLE", "model_name":"gemini-3.1-pro-preview",
  "template": {"type":"chat","messages":[{"role":"user","content":[{"type":"text","text":"<body>"}]}]},
  "template_type":"CHAT", "template_format":"MUSTACHE",
  "invocation_parameters": {"type":"google","google":{"temperature":0.7}},
  "id": "UHJvbXB0VmVyc2lvbjo2" }     // base64("PromptVersion:6") — this is the VERSION id
```
- The template string is wrapped into a chat object. To read a body back:
  `template.messages[0].content[0].text`.
- Calling again with the SAME `name` creates a NEW version of that prompt (returns a new version id).
- Granum sets `model_provider="GOOGLE"`, `model_name="gemini-3.1-pro-preview"` so the Phoenix UI
  renders the right provider (cosmetic — generation runs through our own Vertex client, not Phoenix).

### `add-prompt-version-tag` — tag a version
```json
inputSchema: { "prompt_version_id": {"type":"string"},   // required
               "name":              {"type":"string"},   // required — the tag name
               "description":       {"type":"string"} }
```
- Response via MCP: text `Successfully added tag "production" to prompt version <vid>`.
  (Tool description says "no content (204)" but the MCP layer returns a success sentence.)
- **Move-semantic**: re-tagging `production` onto a new version strips it from the prior version.
  This is Granum's atomic champion-swap primitive.

### `list-prompts` — all prompts (NOT version- or tag-aware)
```json
inputSchema: { "limit": {"type":"number","default":100,"max":100,"min":1} }   // no name filter!
```
**Response** = bare JSON array (adapter wraps as `{"items":[...]}`):
```json
[ { "name":"granumprobe_schema_check", "description":"", "source_prompt_id":null,
    "metadata":{}, "id":"UHJvbXB0OjQ=" } ]    // base64("Prompt:4") — this is the PROMPT id
```
- No `tags`, no version info, no prefix filter, **hard cap 100, no pagination cursor**.
  Granum logs a warning if a space ever exceeds 100 prompts (no silent truncation).

### `get-prompt-version-by-tag` — resolve a tag → version (the champion lookup)
```json
inputSchema: { "prompt_identifier": {"type":"string"},  // required — name or id
               "tag_name":          {"type":"string"} }  // required
```
- **SUCCESS** → the version object (same shape as upsert response): `id` = version id,
  `template` = chat object, `model_provider`/`model_name`, etc.
- **MISS** (tag absent OR prompt absent) → `isError=True`, text is a 404 line, e.g.
  `https://app.phoenix.arize.com/.../v1/prompts/<name>/tags/<tag>: 404 Not Found`.
  The adapter raises `PhoenixToolError`; `list_active_prompts` treats that as "no champion → skip".

### Other prompt reads (available, not all used yet)
`get-latest-prompt(prompt_identifier)`, `get-prompt(prompt_identifier[,tag,version_id])`,
`get-prompt-by-identifier(prompt_identifier)`, `get-prompt-version(prompt_version_id)` — all return
the same version-object shape (`id`, `template`, model config).

---

## Apoptosis (Path B) — REST only, MCP has no tag-removal

There is **no MCP tool to remove a tag**. Confirmed via REST:

| Verb | Route | Result |
|---|---|---|
| `DELETE` | `/v1/prompt_versions/{version_id}/tags/{tag_name}` | **204** (404 if absent — idempotent) |
| `GET` | `/v1/prompt_versions/{version_id}/tags` | **200** `{"data":[...],"next_cursor":null}` |

`tombstone(version_id)` = REST `DELETE .../tags/production` then MCP `add-prompt-version-tag(version_id,"tombstoned")`.
Version stays immutable in the registry → audit history preserved.

---

## Dataset tools (Phase B — outcome writeback)

### `add-dataset-examples`
```json
inputSchema: { "dataset_name": {"type":"string"},               // required
               "examples": [ { "input":  {object},               // required
                               "output": {object},               // required
                               "metadata": {object} } ] }        // optional
```
- **"Add examples to an existing dataset"** — there is **no MCP `create-dataset`**. A dataset
  must pre-exist (create via REST/UI). Granum's `add_dataset_examples` wraps flat analytics rows
  as `{"input":{}, "output":<row>, "metadata":{}}`; cycle step-7 writeback is best-effort
  (logs a warning if the dataset is absent) so a missing dataset never aborts the evolution core.

Reads: `get-dataset`, `get-dataset-examples` (`dataset_name`|`dataset_id`, optional `splits`/`version_id`),
`get-dataset-experiments`, `get-experiment-by-id`.

---

## Tracing tools (Phase B — observability)

- `get-spans`: `{project_identifier, names[], span_kinds[], status_codes[], trace_ids[], start_time, end_time, limit≤1000, cursor, include_annotations}`. **No generic `filter` string** (Phase 1.3 passed `filter` — wrong).
- `get-span-annotations`: `{span_ids[]` (req)`, project_identifier, include_/exclude_annotation_names[], limit≤1000, cursor}`.
- `list-traces`: `{project_identifier, last_n_minutes, since, limit≤100, include_annotations}`.
- `get-trace`: `{trace_id` (req)`, project_identifier, include_annotations}`.
- Sessions: `get-session`, `list-sessions`. Misc: `get-project`, `list-annotation-configs`, `phoenix-support`.

---

## ID cheat-sheet (base64 GlobalIDs)

| Value | Decodes to | Returned by |
|---|---|---|
| `UHJvbXB0OjQ=` | `Prompt:4` | `list-prompts` (`id`) |
| `UHJvbXB0VmVyc2lvbjo2` | `PromptVersion:6` | `upsert-prompt`, `get-*-prompt-version*` (`id`) |

`upsert-prompt` returns **only** the version id. Granum uses the **prompt name** as the logical
`prompt_id` (stable across generations, accepted as `prompt_identifier` everywhere); `version_id`
is the operational handle for tagging/removal.
