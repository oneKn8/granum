"""Phoenix MCP+REST client wrapper — unit tests against the REAL schema.

Retrofitted 2026-06-02 (Phase 1.10b) to the verified-live Phoenix MCP shapes in
`research/phoenix-mcp-schemas.md`:
  - upsert-prompt → `template`, returns version id under `id`, tag-after.
  - add-prompt-version-tag → {prompt_version_id, name}; tags read back via REST.
  - list-prompts → no filter/tags; active resolution via get-prompt-version-by-tag.
  - `/` in names is normalized to `__` (Phoenix strips `/`).
  - apoptosis tag removal is REST DELETE /v1/prompt_versions/{vid}/tags/{tag}.
"""
from unittest.mock import AsyncMock

import httpx
import pytest

from granum.tools.phoenix_client import PhoenixClient, PhoenixToolError, PromptVersion


def _client(mock_mcp, mock_rest=None):
    if mock_rest is None:
        mock_rest = AsyncMock(spec=httpx.AsyncClient)
    return PhoenixClient(
        mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006"
    )


@pytest.mark.asyncio
async def test_upsert_prompt_maps_body_to_template_and_normalizes_name():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"id": "v1"}  # version GlobalID
    client = _client(mock_mcp)

    pv = await client.upsert_prompt(name="aetna_cardiac/bcell_1", body="…appeal template…")

    assert isinstance(pv, PromptVersion)
    # slash normalized to __
    assert pv.prompt_id == "aetna_cardiac__bcell_1"
    assert pv.name == "aetna_cardiac__bcell_1"
    assert pv.version_id == "v1"
    assert "experimental" in pv.tags
    # upsert-prompt was called with `template`, GOOGLE provider, NO `body`/`tags`
    upsert_args = mock_mcp.call_tool.call_args_list[0][0]
    assert upsert_args[0] == "upsert-prompt"
    assert upsert_args[1]["template"] == "…appeal template…"
    assert upsert_args[1]["model_provider"] == "GOOGLE"
    assert "body" not in upsert_args[1]
    assert "tags" not in upsert_args[1]
    # tag applied in a follow-up add-prompt-version-tag call
    tag_args = mock_mcp.call_tool.call_args_list[1][0]
    assert tag_args[0] == "add-prompt-version-tag"
    assert tag_args[1] == {"prompt_version_id": "v1", "name": "experimental"}


@pytest.mark.asyncio
async def test_add_version_tag_uses_mcp_and_reads_back_tags():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.get.return_value = httpx.Response(
        200, json={"data": [{"name": "experimental"}, {"name": "production"}]}
    )
    client = _client(mock_mcp, mock_rest)

    result = await client.add_version_tag("p123", "v1", "production")

    assert "production" in result
    mock_mcp.call_tool.assert_called_once()
    args = mock_mcp.call_tool.call_args[0]
    assert args[0] == "add-prompt-version-tag"
    assert args[1] == {"prompt_version_id": "v1", "name": "production"}
    # tag set read back via REST GET, never via REST DELETE
    mock_rest.get.assert_called_once()
    mock_rest.delete.assert_not_called()


@pytest.mark.asyncio
async def test_remove_version_tag_uses_rest_keyed_on_version_id():
    """Tag removal is REST-only and keyed on the VERSION id, per the live schema."""
    mock_mcp = AsyncMock()
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=204)
    client = _client(mock_mcp, mock_rest)

    await client.remove_version_tag("p123", "v1", "production")

    mock_rest.delete.assert_called_once()
    called_url = mock_rest.delete.call_args[0][0]
    assert "/v1/prompt_versions/v1/tags/production" in called_url
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_tombstone_removes_production_adds_tombstoned():
    """Apoptosis Path B: remove 'production' (REST), add 'tombstoned' (MCP)."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=204)
    client = _client(mock_mcp, mock_rest)

    await client.tombstone("p123", "v1")

    assert mock_rest.delete.call_count == 1
    assert mock_mcp.call_tool.call_count == 1
    mcp_call_args = mock_mcp.call_tool.call_args[0]
    assert mcp_call_args[0] == "add-prompt-version-tag"
    assert mcp_call_args[1]["name"] == "tombstoned"
    assert mcp_call_args[1]["prompt_version_id"] == "v1"


@pytest.mark.asyncio
async def test_tombstone_tolerates_404_on_remove():
    """If 'production' wasn't on the version, REST returns 404; tombstone proceeds."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=404)
    client = _client(mock_mcp, mock_rest)

    await client.tombstone("p123", "v1")  # must not raise

    assert mock_mcp.call_tool.call_count == 1  # add-tombstoned still called


@pytest.mark.asyncio
async def test_list_active_prompts_resolves_production_filters_tombstoned_and_prefix():
    """Real flow: list-prompts → prefix filter → get-prompt-version-by-tag(production).

    bcell_1 → production resolves, kept.
    bcell_2 → production resolves but version is ALSO tombstoned → filtered.
    bcell_3 → production miss (PhoenixToolError) → extinct lineage, skipped.
    other__x → wrong prefix → skipped.
    """
    mock_mcp = AsyncMock()

    async def call_tool(name, args):
        if name == "list-prompts":
            return {
                "items": [
                    {"name": "aetna_cardiac__bcell_1", "id": "P1"},
                    {"name": "aetna_cardiac__bcell_2", "id": "P2"},
                    {"name": "aetna_cardiac__bcell_3", "id": "P3"},
                    {"name": "other__x", "id": "P9"},
                ]
            }
        if name == "get-prompt-version-by-tag":
            ident = args["prompt_identifier"]
            if ident == "aetna_cardiac__bcell_3":
                raise PhoenixToolError("404 Not Found")
            return {"id": "v_" + ident, "template": "body of " + ident}
        return {}

    mock_mcp.call_tool.side_effect = call_tool

    mock_rest = AsyncMock(spec=httpx.AsyncClient)

    async def rest_get(url):
        if "v_aetna_cardiac__bcell_2" in url:
            return httpx.Response(
                200, json={"data": [{"name": "production"}, {"name": "tombstoned"}]}
            )
        return httpx.Response(200, json={"data": [{"name": "production"}]})

    mock_rest.get.side_effect = rest_get
    client = _client(mock_mcp, mock_rest)

    active = await client.list_active_prompts(name_prefix="aetna_cardiac/")

    assert {p.prompt_id for p in active} == {"aetna_cardiac__bcell_1"}
    p = active[0]
    assert p.version_id == "v_aetna_cardiac__bcell_1"
    assert p.body == "body of aetna_cardiac__bcell_1"
    assert "production" in p.tags


@pytest.mark.asyncio
async def test_list_active_prompts_extracts_body_from_chat_template():
    """get-prompt-version-by-tag returns a chat-wrapped template; body is unwrapped."""
    mock_mcp = AsyncMock()

    async def call_tool(name, args):
        if name == "list-prompts":
            return {"items": [{"name": "aetna_cardiac__bcell_1", "id": "P1"}]}
        if name == "get-prompt-version-by-tag":
            return {
                "id": "v9",
                "template": {
                    "type": "chat",
                    "messages": [
                        {"role": "user", "content": [
                            {"type": "text", "text": "the real appeal body"}
                        ]}
                    ],
                },
            }
        return {}

    mock_mcp.call_tool.side_effect = call_tool
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.get.return_value = httpx.Response(200, json={"data": [{"name": "production"}]})
    client = _client(mock_mcp, mock_rest)

    active = await client.list_active_prompts(name_prefix="aetna_cardiac/")

    assert len(active) == 1
    assert active[0].body == "the real appeal body"


@pytest.mark.asyncio
async def test_add_dataset_examples_wraps_flat_rows():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    client = _client(mock_mcp)

    await client.add_dataset_examples(
        dataset_name="granum/aetna_cardiac/outcomes",
        examples=[{"denial_id": "d1", "winner": "p1", "score": 8.4}],
    )

    mock_mcp.call_tool.assert_called_once()
    name, payload = mock_mcp.call_tool.call_args[0]
    assert name == "add-dataset-examples"
    assert payload["dataset_name"] == "granum/aetna_cardiac/outcomes"
    ex = payload["examples"][0]
    assert set(ex.keys()) == {"input", "output", "metadata"}
    assert ex["output"]["denial_id"] == "d1"


@pytest.mark.asyncio
async def test_list_all_prompts_returns_raw_items():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"items": [{"name": "a", "id": "P1"}, {"name": "b", "id": "P2"}]}
    client = _client(mock_mcp)
    items = await client.list_all_prompts()
    assert [i["name"] for i in items] == ["a", "b"]


@pytest.mark.asyncio
async def test_delete_prompt_uses_rest():
    mock_mcp = AsyncMock()
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(204)
    client = _client(mock_mcp, mock_rest)
    await client.delete_prompt("P1")
    mock_rest.delete.assert_called_once()
    assert "/v1/prompts/P1" in mock_rest.delete.call_args[0][0]
    mock_mcp.call_tool.assert_not_called()


# === Co-evolution: dual-lineage state + writeback ===


@pytest.mark.asyncio
async def test_list_coevolution_state_returns_writers_and_payers_separately():
    """Returns (writers, payers); the {cell}__ vs {cell}_payer__ prefixes don't bleed."""
    mock_mcp = AsyncMock()

    async def call_tool(name, args):
        if name == "list-prompts":
            return {
                "items": [
                    {"name": "aetna_cardiac__bcell_1", "id": "P1"},
                    {"name": "aetna_cardiac__bcell_2", "id": "P2"},
                    {"name": "aetna_cardiac_payer__strict", "id": "P3"},
                ]
            }
        if name == "get-prompt-version-by-tag":
            ident = args["prompt_identifier"]
            return {"id": "v_" + ident, "template": ident}
        return {}

    mock_mcp.call_tool.side_effect = call_tool
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.get.return_value = httpx.Response(200, json={"data": [{"name": "production"}]})
    client = _client(mock_mcp, mock_rest)

    writers, payers = await client.list_coevolution_state(cell="aetna_cardiac")

    assert [w.prompt_id for w in writers] == [
        "aetna_cardiac__bcell_1",
        "aetna_cardiac__bcell_2",
    ]
    assert [p.prompt_id for p in payers] == ["aetna_cardiac_payer__strict"]


@pytest.mark.asyncio
async def test_list_coevolution_state_payer_never_bleeds_into_writers():
    """A payer-prefixed prompt must not satisfy the writer prefix and vice versa."""
    mock_mcp = AsyncMock()

    async def call_tool(name, args):
        if name == "list-prompts":
            return {
                "items": [
                    {"name": "aetna_cardiac__bcell_1", "id": "P1"},
                    {"name": "aetna_cardiac_payer__strict", "id": "P2"},
                ]
            }
        if name == "get-prompt-version-by-tag":
            return {"id": "v_" + args["prompt_identifier"], "template": "x"}
        return {}

    mock_mcp.call_tool.side_effect = call_tool
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.get.return_value = httpx.Response(200, json={"data": [{"name": "production"}]})
    client = _client(mock_mcp, mock_rest)

    writers, payers = await client.list_coevolution_state(cell="aetna_cardiac")

    writer_names = {w.name for w in writers}
    payer_names = {p.name for p in payers}
    assert "aetna_cardiac_payer__strict" not in writer_names
    assert "aetna_cardiac__bcell_1" not in payer_names


@pytest.mark.asyncio
async def test_add_coevolution_example_writes_correct_dataset_name():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    client = _client(mock_mcp)

    await client.add_coevolution_example(
        cell="aetna_cardiac",
        round_index=3,
        writer_id="pw_winner",
        payer_id="pp_winner",
        defensibility_composite=7.2,
        english_feedback="Writer cited CPB 0119 §IV.A directly.",
    )

    mock_mcp.call_tool.assert_called_once()
    name, payload = mock_mcp.call_tool.call_args[0]
    assert name == "add-dataset-examples"
    assert payload["dataset_name"] == "granum/aetna_cardiac/coevolution"


@pytest.mark.asyncio
async def test_add_coevolution_example_payload_schema():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    client = _client(mock_mcp)

    await client.add_coevolution_example(
        cell="aetna_cardiac",
        round_index=3,
        writer_id="pw_winner",
        payer_id="pp_winner",
        defensibility_composite=7.2,
        english_feedback="Writer cited CPB 0119 §IV.A directly.",
    )

    ex = mock_mcp.call_tool.call_args[0][1]["examples"][0]
    assert set(ex.keys()) == {"input", "output", "metadata"}
    row = ex["output"]
    assert set(row.keys()) == {
        "round_index",
        "writer_winner_id",
        "payer_winner_id",
        "defensibility_composite",
        "english_feedback",
    }
    assert row["round_index"] == 3
    assert row["writer_winner_id"] == "pw_winner"
    assert row["payer_winner_id"] == "pp_winner"
    assert row["defensibility_composite"] == 7.2
    assert row["english_feedback"] == "Writer cited CPB 0119 §IV.A directly."


@pytest.mark.asyncio
async def test_read_self_improvement_history_reads_own_telemetry():
    """The Arize bonus loop: read prior-generation telemetry back from Phoenix
    spans (get-spans) and return the per-generation trajectory ascending."""
    from granum.center.observability import GenerationObservation

    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {
        "spans": [
            {
                "name": "granum.cycle.aetna_cardiac",
                "start_time": "2026-06-04T00:01:00Z",
                "attributes": {
                    "granum.cell": "aetna_cardiac", "granum.generation": 1,
                    "granum.winner_fitness": 5.4,
                    "granum.judge_critique": "citations not section-level",
                },
            },
            {
                "name": "granum.cycle.aetna_cardiac",
                "start_time": "2026-06-04T00:00:00Z",
                "attributes": {
                    "granum.cell": "aetna_cardiac", "granum.generation": 0,
                    "granum.winner_fitness": 4.0, "granum.judge_critique": "naive",
                },
            },
            {"name": "granum.cycle.tournament", "start_time": "t", "attributes": {}},
        ]
    }
    client = _client(mock_mcp)
    hist = await client.read_self_improvement_history(
        cell="aetna_cardiac", project_name="granum"
    )

    assert mock_mcp.call_tool.await_args[0][0] == "get-spans"
    assert all(isinstance(o, GenerationObservation) for o in hist)
    assert [o.generation for o in hist] == [0, 1]
    assert hist[1].critique == "citations not section-level"
