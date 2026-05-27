from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from granum.center.defensibility_judge import DefensibilityJudge, DefensibilityScore
from granum.data.gold import GoldAppeal


def _sample(
    *,
    cs: int = 7,
    pcq: int = 7,
    pc: int = 7,
    arg: int = 7,
    defn: int = 7,
    feedback: str = "ok",
) -> str:
    return (
        '{"clinical_specificity": ' + str(cs) + ", "
        '"policy_citation_quality": ' + str(pcq) + ", "
        '"procedural_compliance": ' + str(pc) + ", "
        '"argumentative_structure": ' + str(arg) + ", "
        '"defensibility": ' + str(defn) + ", "
        '"english_feedback": "' + feedback + '"}'
    )


def _gold(text: str = "reference appeal A", score: int = 9) -> GoldAppeal:
    return GoldAppeal(
        denial_id="d1",
        appeal_text=text,
        outcome="overturned",
        judge_score=score,
        citations=["Aetna CPB 0119"],
    )


@pytest.mark.asyncio
async def test_score_returns_defensibility_score_dataclass() -> None:
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        _sample(cs=7, pcq=8, pc=8, arg=7, defn=7, feedback="first"),
        _sample(cs=8, pcq=8, pc=8, arg=8, defn=8, feedback="second"),
        _sample(cs=6, pcq=7, pc=8, arg=7, defn=6, feedback="third"),
    ]
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    score = await judge.score(
        candidate_appeal="cand",
        payer_denial_response="payer denied",
        reference_set=[_gold()],
    )
    assert isinstance(score, DefensibilityScore)
    assert isinstance(score.clinical_specificity, int)
    assert isinstance(score.policy_citation_quality, int)
    assert isinstance(score.procedural_compliance, int)
    assert isinstance(score.argumentative_structure, int)
    assert isinstance(score.defensibility, int)
    assert isinstance(score.english_feedback, str)


@pytest.mark.asyncio
async def test_score_takes_median_per_axis() -> None:
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        _sample(cs=7, pcq=8, pc=8, arg=7, defn=7, feedback="first"),
        _sample(cs=8, pcq=8, pc=8, arg=8, defn=8, feedback="second"),
        _sample(cs=6, pcq=7, pc=8, arg=7, defn=6, feedback="third"),
    ]
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    score = await judge.score(
        candidate_appeal="cand",
        payer_denial_response="payer denied",
        reference_set=[_gold()],
    )
    # Medians of [7,8,6], [8,8,7], [8,8,8], [7,8,7], [7,8,6]
    assert score.clinical_specificity == 7
    assert score.policy_citation_quality == 8
    assert score.procedural_compliance == 8
    assert score.argumentative_structure == 7
    assert score.defensibility == 7


@pytest.mark.asyncio
async def test_score_calls_client_three_times_at_temperature_zero() -> None:
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [_sample()] * 3
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    await judge.score(
        candidate_appeal="cand",
        payer_denial_response="payer denied",
        reference_set=[_gold()],
    )
    assert mock_client.generate.await_count == 3
    for call in mock_client.generate.call_args_list:
        assert call.kwargs.get("temperature") == 0.0


@pytest.mark.asyncio
async def test_score_uses_first_samples_english_feedback() -> None:
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        _sample(feedback="ALPHA"),
        _sample(feedback="BETA"),
        _sample(feedback="GAMMA"),
    ]
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    score = await judge.score(
        candidate_appeal="cand",
        payer_denial_response="payer denied",
        reference_set=[_gold()],
    )
    assert score.english_feedback == "ALPHA"


def test_composite_is_mean_of_five_axes() -> None:
    score = DefensibilityScore(
        clinical_specificity=5,
        policy_citation_quality=6,
        procedural_compliance=7,
        argumentative_structure=8,
        defensibility=9,
        english_feedback="x",
    )
    assert score.composite == 7.0


def test_build_prompt_includes_all_three_inputs_and_rubric_headers(tmp_path) -> None:
    # Use the real default rubric path so we exercise the file load
    mock_client = AsyncMock()
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    gold = _gold(text="GOLD_APPEAL_BODY_XYZ", score=9)
    prompt = judge._build_prompt(
        "CANDIDATE_APPEAL_BODY_123",
        "PAYER_DENIAL_BODY_456",
        [gold],
    )
    # Rubric body present (rubric file exists in data/)
    rubric_text = judge._load_rubric()
    assert rubric_text  # sanity: rubric loaded
    assert rubric_text in prompt
    # Candidate verbatim
    assert "CANDIDATE_APPEAL_BODY_123" in prompt
    # Payer denial verbatim
    assert "PAYER_DENIAL_BODY_456" in prompt
    # Gold reference appeal text present
    assert "GOLD_APPEAL_BODY_XYZ" in prompt
    # Section headers
    assert "## Reference appeals" in prompt
    assert "## Payer denial response (adversary)" in prompt
    assert "## Candidate appeal (to be defended)" in prompt


@pytest.mark.asyncio
async def test_score_handles_empty_reference_set_gracefully() -> None:
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [_sample()] * 3
    judge = DefensibilityJudge(client=mock_client, model="gemini-3-pro")
    # Should not crash
    score = await judge.score(
        candidate_appeal="cand",
        payer_denial_response="payer denied",
        reference_set=[],
    )
    assert isinstance(score, DefensibilityScore)
    # Direct prompt build with empty refs should also work and still have headers
    prompt = judge._build_prompt("cand", "payer denied", [])
    assert "## Reference appeals" in prompt
    assert "## Payer denial response (adversary)" in prompt
    assert "## Candidate appeal (to be defended)" in prompt
