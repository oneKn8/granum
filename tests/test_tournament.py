import pytest
from unittest.mock import AsyncMock

from granum.center.tournament import Tournament, TournamentResult
from granum.center.judge import JudgeScore


@pytest.mark.asyncio
async def test_tournament_selects_highest_composite_score():
    mock_judge = AsyncMock()
    mock_judge.score.side_effect = [
        JudgeScore(7, 7, 7, 7, 7, "ok"),       # composite 7.0
        JudgeScore(9, 8, 8, 9, 8, "best"),     # composite 8.4 ← winner
        JudgeScore(6, 6, 7, 6, 6, "poor"),     # composite 6.2
    ]
    candidates = [
        ("p1", "v1", "appeal A"),
        ("p2", "v1", "appeal B"),
        ("p3", "v1", "appeal C"),
    ]
    t = Tournament(judge=mock_judge, gold=[])
    result = await t.run(candidates=candidates)
    assert isinstance(result, TournamentResult)
    assert result.winner == ("p2", "v1", "appeal B")
    assert len(result.losers) == 2
    assert result.winner_score.composite == 8.4


@pytest.mark.asyncio
async def test_tournament_breaks_ties_by_lower_prompt_id():
    mock_judge = AsyncMock()
    same = JudgeScore(7, 7, 7, 7, 7, "tie")
    mock_judge.score.side_effect = [same, same, same]
    candidates = [
        ("p3", "v1", "a"),
        ("p1", "v1", "b"),
        ("p2", "v1", "c"),
    ]
    t = Tournament(judge=mock_judge, gold=[])
    result = await t.run(candidates=candidates)
    # Tie → lowest prompt_id wins
    assert result.winner[0] == "p1"


@pytest.mark.asyncio
async def test_tournament_runs_concurrently():
    """Verify all judge calls happen via gather, not sequentially."""
    import asyncio

    call_order: list[int] = []

    async def slow_score(*args, **kwargs):
        call_order.append(len(call_order))
        await asyncio.sleep(0.01)
        return JudgeScore(5, 5, 5, 5, 5, "x")

    mock_judge = AsyncMock()
    mock_judge.score.side_effect = slow_score
    candidates = [("p1", "v1", "a"), ("p2", "v1", "b"), ("p3", "v1", "c")]
    t = Tournament(judge=mock_judge, gold=[])
    start = asyncio.get_event_loop().time()
    await t.run(candidates=candidates)
    elapsed = asyncio.get_event_loop().time() - start
    # If sequential: ~0.03s. If concurrent via gather: ~0.01s.
    assert elapsed < 0.025
