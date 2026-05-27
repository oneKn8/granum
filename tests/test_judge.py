import pytest
from unittest.mock import AsyncMock

from granum.center.judge import LLMJudge, JudgeScore
from granum.data.gold import GoldAppeal


@pytest.mark.asyncio
async def test_judge_returns_median_of_three_runs():
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        '{"clinical_specificity": 7, "policy_citation_quality": 8, "procedural_compliance": 8, "argumentative_structure": 7, "likelihood_overturn": 7, "english_feedback": "first"}',
        '{"clinical_specificity": 8, "policy_citation_quality": 8, "procedural_compliance": 8, "argumentative_structure": 8, "likelihood_overturn": 8, "english_feedback": "second"}',
        '{"clinical_specificity": 6, "policy_citation_quality": 7, "procedural_compliance": 8, "argumentative_structure": 7, "likelihood_overturn": 6, "english_feedback": "third"}',
    ]
    judge = LLMJudge(client=mock_client, model="gemini-3-pro")
    gold = [
        GoldAppeal(
            denial_id="d1",
            appeal_text="reference appeal A",
            outcome="overturned",
            judge_score=9,
            citations=["Aetna CPB 0119"],
        )
    ]
    score = await judge.score(candidate_appeal="cand", reference_set=gold)
    assert isinstance(score, JudgeScore)
    # Medians: clinical 7, policy 8, procedural 8, argumentative 7, likelihood 7
    assert score.clinical_specificity == 7
    assert score.policy_citation_quality == 8
    assert score.procedural_compliance == 8
    assert score.argumentative_structure == 7
    assert score.likelihood_overturn == 7
    # English feedback from first run (representative)
    assert score.english_feedback == "first"


@pytest.mark.asyncio
async def test_composite_score_is_mean_of_axes():
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        '{"clinical_specificity": 10, "policy_citation_quality": 10, "procedural_compliance": 10, "argumentative_structure": 10, "likelihood_overturn": 10, "english_feedback": "x"}',
    ] * 3
    judge = LLMJudge(client=mock_client, model="gemini-3-pro")
    score = await judge.score(candidate_appeal="cand", reference_set=[])
    assert score.composite == 10.0


@pytest.mark.asyncio
async def test_judge_temperature_is_zero():
    """For determinism we want temperature=0."""
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        '{"clinical_specificity": 5, "policy_citation_quality": 5, "procedural_compliance": 5, "argumentative_structure": 5, "likelihood_overturn": 5, "english_feedback": "x"}',
    ] * 3
    judge = LLMJudge(client=mock_client, model="gemini-3-pro")
    await judge.score(candidate_appeal="cand", reference_set=[])
    # All 3 calls had temperature=0
    for call in mock_client.generate.call_args_list:
        assert call.kwargs.get("temperature") == 0.0
