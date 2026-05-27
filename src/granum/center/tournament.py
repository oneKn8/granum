"""Tournament — concurrent scoring of B-cell candidates against gold antigen.

Returns winner + losers. Ranking: composite score DESC, then prompt_id ASC
for deterministic tie-breaking.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from granum.center.judge import JudgeScore, LLMJudge
from granum.data.gold import GoldAppeal


CandidateRef = tuple[str, str, str]  # (prompt_id, version_id, body)


@dataclass(frozen=True)
class ScoredCandidate:
    prompt_id: str
    version_id: str
    body: str
    score: JudgeScore


@dataclass(frozen=True)
class TournamentResult:
    winner: CandidateRef
    winner_score: JudgeScore
    losers: tuple[CandidateRef, ...]
    all_scores: tuple[ScoredCandidate, ...]


class Tournament:
    def __init__(self, *, judge: LLMJudge, gold: list[GoldAppeal]) -> None:
        self._judge = judge
        self._gold = gold

    async def run(self, *, candidates: list[CandidateRef]) -> TournamentResult:
        if not candidates:
            raise ValueError("Tournament requires at least one candidate")
        scored = await asyncio.gather(
            *[self._score_one(c) for c in candidates]
        )
        # Sort: composite DESC, prompt_id ASC
        ranked = sorted(
            scored,
            key=lambda s: (-s.score.composite, s.prompt_id),
        )
        winner_s = ranked[0]
        return TournamentResult(
            winner=(winner_s.prompt_id, winner_s.version_id, winner_s.body),
            winner_score=winner_s.score,
            losers=tuple(
                (s.prompt_id, s.version_id, s.body) for s in ranked[1:]
            ),
            all_scores=tuple(scored),
        )

    async def _score_one(self, candidate: CandidateRef) -> ScoredCandidate:
        prompt_id, version_id, body = candidate
        score = await self._judge.score(
            candidate_appeal=body, reference_set=self._gold
        )
        return ScoredCandidate(
            prompt_id=prompt_id, version_id=version_id, body=body, score=score
        )
