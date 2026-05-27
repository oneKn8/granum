"""Phoenix MCP+REST client wrapper — unit tests with mocked transports.

This client is the SOLE seam between Granum and Phoenix. All Phoenix tool
names and REST paths appear ONLY here. Business logic talks to this client
via typed methods. Path B apoptosis (tag-based) is enforced.
"""
from unittest.mock import AsyncMock

import httpx
import pytest

from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_upsert_prompt_creates_new_version():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {
        "promptId": "p123",
        "versionId": "v1",
        "tags": ["experimental"],
    }
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    pv = await client.upsert_prompt(name="aetna_cardiac/bcell_1", body="…appeal template…")
    assert isinstance(pv, PromptVersion)
    assert pv.prompt_id == "p123"
    assert "experimental" in pv.tags


@pytest.mark.asyncio
async def test_add_version_tag_uses_mcp():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"tags": ["experimental", "production"]}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    result = await client.add_version_tag("p123", "v1", "production")
    assert "production" in result
    # Verify MCP, not REST, was used
    mock_mcp.call_tool.assert_called_once()
    mock_rest.delete.assert_not_called()


@pytest.mark.asyncio
async def test_remove_version_tag_uses_rest():
    """Tag removal is REST-only per Phoenix MCP audit; client must use REST."""
    mock_mcp = AsyncMock()
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=204)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.remove_version_tag("p123", "v1", "production")
    # REST DELETE was called
    mock_rest.delete.assert_called_once()
    called_url = mock_rest.delete.call_args[0][0]
    assert "/v1/prompt_versions/v1/tags/production" in called_url
    # MCP was NOT called (tag removal not in MCP)
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_tombstone_removes_production_adds_tombstoned():
    """Functional apoptosis: remove 'production' tag (REST), add 'tombstoned' tag (MCP)."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"tags": ["experimental", "tombstoned"]}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=204)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.tombstone("p123", "v1")
    # Both transports used
    assert mock_rest.delete.call_count == 1
    assert mock_mcp.call_tool.call_count == 1
    # MCP call was add-prompt-version-tag with 'tombstoned'
    mcp_call_args = mock_mcp.call_tool.call_args
    assert mcp_call_args[0][0] == "add-prompt-version-tag"
    assert mcp_call_args[0][1]["tag"] == "tombstoned"


@pytest.mark.asyncio
async def test_tombstone_tolerates_404_on_remove():
    """If 'production' tag wasn't on the version, REST returns 404; tombstone proceeds."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"tags": ["experimental", "tombstoned"]}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    mock_rest.delete.return_value = httpx.Response(status_code=404)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    # Should not raise
    await client.tombstone("p123", "v1")
    assert mock_mcp.call_tool.call_count == 1  # add-tombstoned still called


@pytest.mark.asyncio
async def test_list_prompts_returns_active_population_only():
    """Selection logic must filter out tombstoned versions."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {
        "prompts": [
            {"promptId": "p1", "versionId": "v1", "tags": ["production"], "body": "alive 1"},
            {"promptId": "p2", "versionId": "v1", "tags": ["production", "tombstoned"], "body": "dead"},
            {"promptId": "p3", "versionId": "v1", "tags": ["production"], "body": "alive 2"},
        ]
    }
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    active = await client.list_active_prompts(name_prefix="aetna_cardiac/")
    assert len(active) == 2
    assert {p.prompt_id for p in active} == {"p1", "p3"}


@pytest.mark.asyncio
async def test_add_dataset_examples_via_mcp():
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = None
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.add_dataset_examples(
        dataset_name="granum/aetna_cardiac/outcomes",
        examples=[{"denial_id": "d1", "winner": "p1", "score": 8.4}],
    )
    mock_mcp.call_tool.assert_called_once()
    args = mock_mcp.call_tool.call_args[0]
    assert args[0] == "add-dataset-examples"


# === Co-evolution: dual-lineage state + writeback ===


@pytest.mark.asyncio
async def test_list_coevolution_state_returns_writers_and_payers_separately():
    """Returns (writers, payers) tuple from two separate prefix queries."""
    mock_mcp = AsyncMock()

    async def call_tool(name: str, arguments: dict) -> dict:
        prefix = arguments.get("namePrefix", "")
        if prefix == "aetna_cardiac/":
            return {
                "prompts": [
                    {"promptId": "pw1", "versionId": "v1", "tags": ["production"], "body": "writer1", "name": "aetna_cardiac/bcell_1"},
                    {"promptId": "pw2", "versionId": "v1", "tags": ["production"], "body": "writer2", "name": "aetna_cardiac/bcell_2"},
                ]
            }
        if prefix == "aetna_cardiac_payer/":
            return {
                "prompts": [
                    {"promptId": "pp1", "versionId": "v1", "tags": ["production"], "body": "payer1", "name": "aetna_cardiac_payer/strict"},
                ]
            }
        return {"prompts": []}

    mock_mcp.call_tool.side_effect = call_tool
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    writers, payers = await client.list_coevolution_state(cell="aetna_cardiac")
    assert [w.prompt_id for w in writers] == ["pw1", "pw2"]
    assert [p.prompt_id for p in payers] == ["pp1"]


@pytest.mark.asyncio
async def test_list_coevolution_state_uses_correct_prefixes():
    """Verifies the two list-prompts calls use {cell}/ and {cell}_payer/ prefixes."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"prompts": []}
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.list_coevolution_state(cell="aetna_cardiac")
    assert mock_mcp.call_tool.call_count == 2
    prefixes_called = [
        call.args[1]["namePrefix"] for call in mock_mcp.call_tool.call_args_list
    ]
    assert "aetna_cardiac/" in prefixes_called
    assert "aetna_cardiac_payer/" in prefixes_called


@pytest.mark.asyncio
async def test_add_coevolution_example_writes_correct_dataset_name():
    """Writeback targets the granum/{cell}/coevolution dataset."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = None
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.add_coevolution_example(
        cell="aetna_cardiac",
        round_index=3,
        writer_id="pw_winner",
        payer_id="pp_winner",
        defensibility_composite=7.2,
        english_feedback="Writer cited CPB 0119 §IV.A directly.",
    )
    mock_mcp.call_tool.assert_called_once()
    args = mock_mcp.call_tool.call_args[0]
    assert args[0] == "add-dataset-examples"
    assert args[1]["datasetName"] == "granum/aetna_cardiac/coevolution"


@pytest.mark.asyncio
async def test_add_coevolution_example_payload_schema():
    """Payload contains exactly the 5 required keys with correct values."""
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = None
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    client = PhoenixClient(mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006")
    await client.add_coevolution_example(
        cell="aetna_cardiac",
        round_index=3,
        writer_id="pw_winner",
        payer_id="pp_winner",
        defensibility_composite=7.2,
        english_feedback="Writer cited CPB 0119 §IV.A directly.",
    )
    examples = mock_mcp.call_tool.call_args[0][1]["examples"]
    assert len(examples) == 1
    row = examples[0]
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
