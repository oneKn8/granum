"""Tests for transfer-edge metadata writeback (Task 4.4).

Two layers covered:

1. ``PhoenixClient.add_transfer_edge`` + ``list_transfer_edges`` — direct
   MCP-mocked tests for the dataset writeback + read-back primitives.
2. ``promote_transfer`` wiring — confirms a successful promotion auto-records
   one transfer edge, and a failed promotion records none.

Dataset name is ``granum/transfer_edges`` (single shared dataset across all
cells — UI reads it once to render the cross-cell lineage tree).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from granum.tools.phoenix_client import (
    PhoenixClient,
    PromptVersion,
    TransferEdge,
)
from granum.transfer.trial import TransferTrial, promote_transfer


# === PhoenixClient layer — mock MCP session ===


def _make_client(mock_mcp: AsyncMock) -> PhoenixClient:
    mock_rest = AsyncMock(spec=httpx.AsyncClient)
    return PhoenixClient(
        mcp_session=mock_mcp, rest=mock_rest, base_url="http://localhost:6006"
    )


@pytest.mark.asyncio
async def test_add_transfer_edge_writes_correct_dataset_name_and_payload() -> None:
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {}
    client = _make_client(mock_mcp)

    await client.add_transfer_edge(
        source_cell="aetna_cardiac",
        target_cell="united_oncology",
        source_prompt_id="bc_ae_writer_007",
        target_prompt_id="bc_uo_transferred_001",
        mean_score=7.8,
        p_value=0.012,
    )

    mock_mcp.call_tool.assert_awaited_once()
    tool_name, payload = mock_mcp.call_tool.call_args[0]
    assert tool_name == "add-dataset-examples"
    assert payload["datasetName"] == "granum/transfer_edges"
    assert len(payload["examples"]) == 1
    row = payload["examples"][0]
    assert row == {
        "source_cell": "aetna_cardiac",
        "target_cell": "united_oncology",
        "source_prompt_id": "bc_ae_writer_007",
        "target_prompt_id": "bc_uo_transferred_001",
        "mean_score": 7.8,
        "p_value": 0.012,
    }


@pytest.mark.asyncio
async def test_list_transfer_edges_returns_typed_edges() -> None:
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {
        "examples": [
            {
                "source_cell": "aetna_cardiac",
                "target_cell": "united_oncology",
                "source_prompt_id": "src_1",
                "target_prompt_id": "tgt_1",
                "mean_score": 7.0,
                "p_value": 0.01,
            },
            {
                "source_cell": "cigna_cardiac",
                "target_cell": "humana_cardiac",
                "source_prompt_id": "src_2",
                "target_prompt_id": "tgt_2",
                "mean_score": 8.0,
                "p_value": 0.02,
            },
            {
                "source_cell": "aetna_cardiac",
                "target_cell": "cigna_cardiac",
                "source_prompt_id": "src_3",
                "target_prompt_id": "tgt_3",
                "mean_score": 6.5,
                "p_value": 0.03,
            },
        ]
    }
    client = _make_client(mock_mcp)

    edges = await client.list_transfer_edges()

    assert len(edges) == 3
    assert all(isinstance(e, TransferEdge) for e in edges)
    assert edges[0].source_cell == "aetna_cardiac"
    assert edges[0].target_cell == "united_oncology"
    assert edges[0].mean_score == 7.0
    assert edges[2].source_prompt_id == "src_3"


@pytest.mark.asyncio
async def test_list_transfer_edges_filters_by_cell_argument() -> None:
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {
        "examples": [
            {
                "source_cell": "aetna_cardiac",
                "target_cell": "united_oncology",
                "source_prompt_id": "src_1",
                "target_prompt_id": "tgt_1",
                "mean_score": 7.0,
                "p_value": 0.01,
            },
            {
                "source_cell": "cigna_cardiac",
                "target_cell": "humana_cardiac",
                "source_prompt_id": "src_2",
                "target_prompt_id": "tgt_2",
                "mean_score": 8.0,
                "p_value": 0.02,
            },
            {
                "source_cell": "aetna_cardiac",
                "target_cell": "cigna_cardiac",
                "source_prompt_id": "src_3",
                "target_prompt_id": "tgt_3",
                "mean_score": 6.5,
                "p_value": 0.03,
            },
        ]
    }
    client = _make_client(mock_mcp)

    edges = await client.list_transfer_edges(cell="aetna_cardiac")

    assert len(edges) == 2
    src_ids = {e.source_prompt_id for e in edges}
    assert src_ids == {"src_1", "src_3"}


@pytest.mark.asyncio
async def test_list_transfer_edges_returns_empty_list_when_dataset_empty() -> None:
    mock_mcp = AsyncMock()
    mock_mcp.call_tool.return_value = {"examples": []}
    client = _make_client(mock_mcp)

    edges = await client.list_transfer_edges()

    assert edges == []


# === promote_transfer wiring — mock PhoenixClient ===


def _make_trial(
    *,
    p_value: float,
    mean_score: float,
    baseline: float = 5.0,
    prompt_body: str = "appeal body",
) -> TransferTrial:
    return TransferTrial(
        source_cell="aetna_cardiac",
        target_cell="united_oncology",
        prompt_id="bc_ae_writer_001",
        prompt_version_id="v1",
        prompt_body=prompt_body,
        scores=(7.0, 7.0, 7.0, 7.0, 7.0),
        mean_score=mean_score,
        p_value=p_value,
        baseline_target_fitness=baseline,
    )


def _mock_phoenix_with_upsert(new_prompt_id: str = "new_id") -> AsyncMock:
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.upsert_prompt = AsyncMock(
        return_value=PromptVersion(
            prompt_id=new_prompt_id,
            version_id="v1",
            tags=("transferred", "experimental"),
            body="appeal body",
            name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
        )
    )
    phoenix.add_transfer_edge = AsyncMock(return_value=None)
    return phoenix


@pytest.mark.asyncio
async def test_successful_promote_calls_add_transfer_edge() -> None:
    trial = _make_trial(p_value=0.01, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix_with_upsert(new_prompt_id="new_id")

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is not None
    phoenix.add_transfer_edge.assert_awaited_once_with(
        source_cell="aetna_cardiac",
        target_cell="united_oncology",
        source_prompt_id="bc_ae_writer_001",
        target_prompt_id="new_id",
        mean_score=8.0,
        p_value=0.01,
    )


@pytest.mark.asyncio
async def test_failed_promote_does_not_call_add_transfer_edge() -> None:
    # p_value above default 0.05 threshold -> gate fails
    trial = _make_trial(p_value=0.5, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix_with_upsert()

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is None
    assert phoenix.add_transfer_edge.await_count == 0


@pytest.mark.asyncio
async def test_promote_passes_through_phoenix_promptversion_correctly() -> None:
    trial = _make_trial(p_value=0.02, mean_score=9.0, baseline=5.0)
    phoenix = _mock_phoenix_with_upsert(new_prompt_id="newid")

    await promote_transfer(trial, phoenix=phoenix)

    call_kwargs = phoenix.add_transfer_edge.call_args.kwargs
    assert call_kwargs["target_prompt_id"] == "newid"
    assert call_kwargs["source_prompt_id"] == "bc_ae_writer_001"
    assert call_kwargs["mean_score"] == 9.0
    assert call_kwargs["p_value"] == 0.02
