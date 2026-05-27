from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from granum.adversary.payer_agent import PayerAgent
from granum.center.defensibility_judge import DefensibilityJudge, DefensibilityScore
from granum.center.triangular_tournament import (
    PairScore,
    TriangularTournament,
    TriangularTournamentResult,
)
from granum.data.denials import Denial, DenialReason


def _score(defensibility: int, feedback: str = "ok") -> DefensibilityScore:
    return DefensibilityScore(
        clinical_specificity=5,
        policy_citation_quality=5,
        procedural_compliance=5,
        argumentative_structure=5,
        defensibility=defensibility,
        english_feedback=feedback,
    )


def _denial(tag: str = "x") -> Denial:
    return Denial(
        denial_id=f"adv_{tag}",
        payer="aetna",
        diagnosis="cardiac",
        cpt_code="93306",
        icd10_code="I25.10",
        patient_age_range="adv",
        denial_reason=DenialReason.NOT_MEDICALLY_NECESSARY,
        denial_text=f"denial text {tag}",
        submission_date="adversarial",
    )


def _make_tournament(
    *,
    deny_side_effect=None,
    score_side_effect=None,
) -> tuple[TriangularTournament, AsyncMock, AsyncMock]:
    mock_payer = AsyncMock(spec=PayerAgent)
    mock_judge = AsyncMock(spec=DefensibilityJudge)
    if deny_side_effect is None:
        mock_payer.deny.return_value = _denial()
    else:
        mock_payer.deny.side_effect = deny_side_effect
    if score_side_effect is not None:
        mock_judge.score.side_effect = score_side_effect
    tournament = TriangularTournament(
        payer_agent=mock_payer, judge=mock_judge, gold=[]
    )
    return tournament, mock_payer, mock_judge


@pytest.mark.asyncio
async def test_run_executes_full_cross_product_of_writers_and_payers():
    # 2 writers × 3 payers = 6 pairs.
    scores = [_score(5) for _ in range(6)]
    tournament, mock_payer, mock_judge = _make_tournament(
        score_side_effect=scores,
    )
    writers = [
        ("w1", "v1", "appeal A"),
        ("w2", "v1", "appeal B"),
    ]
    payers = [
        ("py1", "v1", "strict"),
        ("py2", "v1", "lenient"),
        ("py3", "v1", "strict"),
    ]
    await tournament.run(writer_candidates=writers, payer_candidates=payers)
    assert mock_payer.deny.await_count == 6
    assert mock_judge.score.await_count == 6


@pytest.mark.asyncio
async def test_writer_winner_ranks_by_mean_defensibility_across_all_payers():
    # Order: (wA,py1), (wA,py2), (wB,py1), (wB,py2)
    # wA: 9, 7 → mean 8.0 ; wB: 6, 4 → mean 5.0
    scores = [_score(9), _score(7), _score(6), _score(4)]
    tournament, _, _ = _make_tournament(score_side_effect=scores)
    writers = [
        ("wA", "v1", "appeal A"),
        ("wB", "v1", "appeal B"),
    ]
    payers = [
        ("py1", "v1", "strict"),
        ("py2", "v1", "lenient"),
    ]
    result = await tournament.run(
        writer_candidates=writers, payer_candidates=payers
    )
    assert result.writer_winner == ("wA", "v1", "appeal A")
    assert len(result.writer_losers) == 1
    assert result.writer_losers[0] == ("wB", "v1", "appeal B")


@pytest.mark.asyncio
async def test_payer_winner_ranks_by_mean_inverse_defensibility():
    # Same fixture as previous test.
    # py1 inverse mean: (10-9 + 10-6)/2 = 2.5
    # py2 inverse mean: (10-7 + 10-4)/2 = 4.5 ← winner
    scores = [_score(9), _score(7), _score(6), _score(4)]
    tournament, _, _ = _make_tournament(score_side_effect=scores)
    writers = [
        ("wA", "v1", "appeal A"),
        ("wB", "v1", "appeal B"),
    ]
    payers = [
        ("py1", "v1", "strict"),
        ("py2", "v1", "lenient"),
    ]
    result = await tournament.run(
        writer_candidates=writers, payer_candidates=payers
    )
    assert result.payer_winner == ("py2", "v1", "lenient")
    assert len(result.payer_losers) == 1
    assert result.payer_losers[0] == ("py1", "v1", "strict")


@pytest.mark.asyncio
async def test_tie_break_by_prompt_id_ascending():
    # All scores equal → tie. Lexicographically smallest prompt_id wins.
    scores = [_score(7), _score(7), _score(7), _score(7)]
    tournament, _, _ = _make_tournament(score_side_effect=scores)
    writers = [
        ("wB", "v1", "appeal B"),
        ("wA", "v1", "appeal A"),
    ]
    payers = [
        ("pyZ", "v1", "strict"),
        ("pyA", "v1", "lenient"),
    ]
    result = await tournament.run(
        writer_candidates=writers, payer_candidates=payers
    )
    assert result.writer_winner[0] == "wA"
    # Payer tie-break also ASC by prompt_id.
    assert result.payer_winner[0] == "pyA"


@pytest.mark.asyncio
async def test_run_raises_on_empty_writer_candidates():
    tournament, _, _ = _make_tournament()
    with pytest.raises(
        ValueError, match="at least one writer and one payer"
    ):
        await tournament.run(
            writer_candidates=[],
            payer_candidates=[("py1", "v1", "strict")],
        )


@pytest.mark.asyncio
async def test_run_raises_on_empty_payer_candidates():
    tournament, _, _ = _make_tournament()
    with pytest.raises(
        ValueError, match="at least one writer and one payer"
    ):
        await tournament.run(
            writer_candidates=[("w1", "v1", "appeal")],
            payer_candidates=[],
        )


@pytest.mark.asyncio
async def test_pair_scores_record_all_writer_payer_combinations():
    scores = [_score(5), _score(5), _score(5), _score(5)]
    tournament, _, _ = _make_tournament(score_side_effect=scores)
    writers = [
        ("wA", "v1", "appeal A"),
        ("wB", "v1", "appeal B"),
    ]
    payers = [
        ("py1", "v1", "strict"),
        ("py2", "v1", "lenient"),
    ]
    result = await tournament.run(
        writer_candidates=writers, payer_candidates=payers
    )
    assert len(result.all_pair_scores) == 4
    for ps in result.all_pair_scores:
        assert isinstance(ps, PairScore)
    pairs = {(ps.writer_id, ps.payer_id) for ps in result.all_pair_scores}
    assert pairs == {
        ("wA", "py1"),
        ("wA", "py2"),
        ("wB", "py1"),
        ("wB", "py2"),
    }


@pytest.mark.asyncio
async def test_writer_winner_mean_defensibility_property_correct():
    # Same fixture as test_writer_winner_ranks_*: winner wA mean = 8.0.
    scores = [_score(9), _score(7), _score(6), _score(4)]
    tournament, _, _ = _make_tournament(score_side_effect=scores)
    writers = [
        ("wA", "v1", "appeal A"),
        ("wB", "v1", "appeal B"),
    ]
    payers = [
        ("py1", "v1", "strict"),
        ("py2", "v1", "lenient"),
    ]
    result = await tournament.run(
        writer_candidates=writers, payer_candidates=payers
    )
    assert isinstance(result, TriangularTournamentResult)
    assert result.writer_winner_mean_defensibility == 8.0
    # And the payer winner's inverse mean = 4.5 from the prior test.
    assert result.payer_winner_mean_inverse_defensibility == 4.5
