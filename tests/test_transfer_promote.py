"""Tests for the transfer-promotion gate (Task 4.3).

`promote_transfer` upserts a successful cross-cell transfer into the target
cell's Phoenix namespace iff BOTH gates pass:
  1. p_value < p_value_threshold (default 0.05)
  2. mean_score >= baseline_target_fitness + lift_threshold (default 1.0)

On gate-fail, returns None and makes ZERO Phoenix calls.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from granum.tools.phoenix_client import PhoenixClient, PromptVersion
from granum.transfer.trial import TransferTrial, promote_transfer


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


def _mock_phoenix() -> AsyncMock:
    phoenix = AsyncMock(spec=PhoenixClient)
    phoenix.upsert_prompt = AsyncMock()
    return phoenix


@pytest.mark.asyncio
async def test_promote_returns_none_when_p_value_above_threshold() -> None:
    trial = _make_trial(p_value=0.1, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix()

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is None
    assert phoenix.upsert_prompt.await_count == 0


@pytest.mark.asyncio
async def test_promote_returns_none_when_lift_below_threshold() -> None:
    trial = _make_trial(p_value=0.01, mean_score=5.5, baseline=5.0)
    phoenix = _mock_phoenix()

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is None
    assert phoenix.upsert_prompt.await_count == 0


@pytest.mark.asyncio
async def test_promote_returns_promptversion_on_pass() -> None:
    trial = _make_trial(p_value=0.01, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix()
    phoenix.upsert_prompt.return_value = PromptVersion(
        prompt_id="new_id",
        version_id="v1",
        tags=("transferred", "experimental"),
        body="appeal body",
        name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
    )

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is not None
    assert result.prompt_id == "new_id"


@pytest.mark.asyncio
async def test_promote_upsert_uses_correct_name_pattern() -> None:
    trial = _make_trial(p_value=0.01, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix()
    phoenix.upsert_prompt.return_value = PromptVersion(
        prompt_id="new_id",
        version_id="v1",
        tags=("transferred", "experimental"),
        body="appeal body",
        name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
    )

    await promote_transfer(trial, phoenix=phoenix)

    phoenix.upsert_prompt.assert_awaited_once_with(
        name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
        body="appeal body",
        tags=("transferred", "experimental"),
    )


@pytest.mark.asyncio
async def test_promote_thresholds_are_customizable() -> None:
    # p_value=0.08 fails default 0.05 gate but passes custom 0.10 gate.
    trial = _make_trial(p_value=0.08, mean_score=8.0, baseline=5.0)
    phoenix = _mock_phoenix()
    phoenix.upsert_prompt.return_value = PromptVersion(
        prompt_id="new_id",
        version_id="v1",
        tags=("transferred", "experimental"),
        body="appeal body",
        name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
    )

    result = await promote_transfer(trial, phoenix=phoenix, p_value_threshold=0.10)

    assert result is not None
    assert result.prompt_id == "new_id"


@pytest.mark.asyncio
async def test_promote_lift_threshold_is_customizable() -> None:
    # Lift = exactly 0.5; with custom lift_threshold=0.5 the >= gate passes.
    trial = _make_trial(p_value=0.01, mean_score=5.5, baseline=5.0)
    phoenix = _mock_phoenix()
    phoenix.upsert_prompt.return_value = PromptVersion(
        prompt_id="new_id",
        version_id="v1",
        tags=("transferred", "experimental"),
        body="appeal body",
        name="united_oncology/transferred_from_aetna_cardiac_bc_ae_writer_001",
    )

    result = await promote_transfer(trial, phoenix=phoenix, lift_threshold=0.5)

    assert result is not None
    assert result.prompt_id == "new_id"


@pytest.mark.asyncio
async def test_promote_passes_only_when_both_thresholds_pass() -> None:
    # p_value good but lift=0 -> gate fails (AND condition).
    trial = _make_trial(p_value=0.01, mean_score=5.0, baseline=5.0)
    phoenix = _mock_phoenix()

    result = await promote_transfer(trial, phoenix=phoenix)

    assert result is None
    assert phoenix.upsert_prompt.await_count == 0
