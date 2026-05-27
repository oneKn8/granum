"""Tests for TransferTrialHarness — N-sample cross-cell evaluation."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.center.judge import JudgeScore, LLMJudge
from granum.data.denials import Denial, DenialReason
from granum.transfer.trial import TransferTrial, TransferTrialHarness


def _judge_score(composite: int) -> JudgeScore:
    return JudgeScore(
        clinical_specificity=composite,
        policy_citation_quality=composite,
        procedural_compliance=composite,
        argumentative_structure=composite,
        likelihood_overturn=composite,
        english_feedback="ok",
    )


def _judge_score_axes(
    clinical: int,
    policy: int,
    procedural: int,
    argument: int,
    likelihood: int,
) -> JudgeScore:
    return JudgeScore(
        clinical_specificity=clinical,
        policy_citation_quality=policy,
        procedural_compliance=procedural,
        argumentative_structure=argument,
        likelihood_overturn=likelihood,
        english_feedback="ok",
    )


_CANNED_DENIAL = Denial(
    denial_id="aetna_cardiac_abc",
    payer="aetna",
    diagnosis="cardiac",
    cpt_code="93306",
    icd10_code="I25.10",
    patient_age_range="55-60",
    denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
    denial_text="synthetic denial text",
    submission_date="2026-03-01",
)


# A prompt body that passes negative selection against
# data/aetna_cardiac/valid_citations.json (Aetna CPB 0119 + 30 days).
_VALID_PROMPT_BODY = (
    "Per Aetna CPB 0119, the requested echocardiogram is supported by "
    "documented worsening symptoms. Appeal deadline: 30 days from notice."
)

_VALID_CITATIONS_PATH = "data/aetna_cardiac/valid_citations.json"
_GOLD_PATH = "data/aetna_cardiac/gold_appeals.jsonl"


def _build_harness(
    judge: LLMJudge,
    denial_factory: MagicMock,
    baseline: float = 5.0,
) -> TransferTrialHarness:
    return TransferTrialHarness(
        judge=judge,
        target_denial_factory=denial_factory,
        target_payer="aetna",
        target_diagnosis="cardiac",
        target_valid_citations_path=_VALID_CITATIONS_PATH,
        target_gold_path=_GOLD_PATH,
        baseline_target_fitness=baseline,
    )


@pytest.mark.asyncio
async def test_trial_returns_transfer_trial_with_correct_fields() -> None:
    judge = AsyncMock(spec=LLMJudge)
    judge.score.side_effect = [
        _judge_score(8),
        _judge_score(7),
        _judge_score(9),
        _judge_score(8),
        _judge_score(7),
    ]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    result = await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p123",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
        seed=0,
    )
    assert isinstance(result, TransferTrial)
    assert result.source_cell == "united_oncology"
    assert result.target_cell == "aetna_cardiac"
    assert result.prompt_id == "p123"
    assert result.prompt_version_id == "v1"
    assert result.prompt_body == _VALID_PROMPT_BODY
    assert result.scores == (8.0, 7.0, 9.0, 8.0, 7.0)
    assert result.mean_score == pytest.approx(7.8)
    assert result.baseline_target_fitness == 5.0
    assert result.n_negative_selection_failures == 0
    assert 0.0 <= result.p_value <= 1.0


@pytest.mark.asyncio
async def test_trial_pvalue_below_threshold_when_scores_significantly_above_baseline() -> None:
    judge = AsyncMock(spec=LLMJudge)
    # 9, 9, 8, 9, 9 → mean 8.8, stdev > 0; well above baseline=5.0
    judge.score.side_effect = [
        _judge_score(9),
        _judge_score(9),
        _judge_score(8),
        _judge_score(9),
        _judge_score(9),
    ]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    result = await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
    )
    assert result.p_value < 0.05


@pytest.mark.asyncio
async def test_trial_pvalue_above_threshold_when_scores_near_baseline() -> None:
    judge = AsyncMock(spec=LLMJudge)
    # Mix of 5/6 axes so composite is slightly above 5.0 with non-zero stdev
    judge.score.side_effect = [
        _judge_score_axes(5, 5, 5, 5, 6),  # composite 5.2
        _judge_score_axes(5, 5, 5, 6, 5),  # 5.2
        _judge_score_axes(5, 5, 5, 5, 5),  # 5.0
        _judge_score_axes(5, 5, 5, 5, 6),  # 5.2
        _judge_score_axes(5, 5, 5, 5, 5),  # 5.0
    ]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    result = await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
    )
    assert result.p_value > 0.05


@pytest.mark.asyncio
async def test_trial_returns_zero_scores_when_negative_selection_fails() -> None:
    judge = AsyncMock(spec=LLMJudge)
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    result = await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body="hello world no citations here",
        n_samples=5,
    )
    assert result.scores == (0.0, 0.0, 0.0, 0.0, 0.0)
    assert result.mean_score == 0.0
    assert result.p_value == 1.0
    assert result.n_negative_selection_failures == 5
    judge.score.assert_not_awaited()


@pytest.mark.asyncio
async def test_trial_calls_denial_factory_n_times() -> None:
    judge = AsyncMock(spec=LLMJudge)
    judge.score.side_effect = [_judge_score(7) for _ in range(5)]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
        seed=10,
    )
    assert factory.call_count == 5
    for call in factory.call_args_list:
        assert call.kwargs["payer"] == "aetna"
        assert call.kwargs["diagnosis"] == "cardiac"
    seeds = [call.kwargs["seed"] for call in factory.call_args_list]
    assert seeds == [10, 11, 12, 13, 14]


@pytest.mark.asyncio
async def test_trial_calls_judge_n_times() -> None:
    judge = AsyncMock(spec=LLMJudge)
    judge.score.side_effect = [_judge_score(7) for _ in range(5)]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
    )
    assert judge.score.await_count == 5


@pytest.mark.asyncio
async def test_trial_raises_on_n_samples_below_two() -> None:
    judge = AsyncMock(spec=LLMJudge)
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    with pytest.raises(ValueError):
        await harness.trial_transfer(
            source_cell="united_oncology",
            target_cell="aetna_cardiac",
            prompt_id="p1",
            prompt_version_id="v1",
            prompt_body=_VALID_PROMPT_BODY,
            n_samples=1,
        )
    with pytest.raises(ValueError):
        await harness.trial_transfer(
            source_cell="united_oncology",
            target_cell="aetna_cardiac",
            prompt_id="p1",
            prompt_version_id="v1",
            prompt_body=_VALID_PROMPT_BODY,
            n_samples=0,
        )


@pytest.mark.asyncio
async def test_trial_degenerate_zero_stdev_above_baseline_gives_zero_p() -> None:
    judge = AsyncMock(spec=LLMJudge)
    judge.score.side_effect = [_judge_score(8) for _ in range(5)]
    factory = MagicMock(return_value=_CANNED_DENIAL)
    harness = _build_harness(judge, factory, baseline=5.0)
    result = await harness.trial_transfer(
        source_cell="united_oncology",
        target_cell="aetna_cardiac",
        prompt_id="p1",
        prompt_version_id="v1",
        prompt_body=_VALID_PROMPT_BODY,
        n_samples=5,
    )
    assert result.mean_score == 8.0
    assert result.p_value == 0.0
