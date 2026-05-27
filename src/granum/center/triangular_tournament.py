"""TriangularTournament — co-evolution of writer × payer populations.

For each (writer, payer) pair across the cross product, the payer agent
produces a denial response specifically targeting the writer's candidate
appeal, then the DefensibilityJudge scores how well the appeal withstood
that denial.

Writers are ranked by mean defensibility across all payers they faced
(higher is better — the appeal that defends best on average wins).
Payers are ranked by mean inverse defensibility (10 - defensibility)
across all writers they attacked (higher is better — the adversary that
extracted the most weakness wins).

Both rankings tie-break by prompt_id ascending for determinism, mirroring
the existing single-population Tournament convention.
"""
from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass

from granum.adversary.payer_agent import PayerAgent
from granum.center.defensibility_judge import DefensibilityJudge, DefensibilityScore
from granum.data.gold import GoldAppeal


WriterRef = tuple[str, str, str]   # (prompt_id, version_id, body)
PayerRef = tuple[str, str, str]    # (prompt_id, version_id, persona_id)


@dataclass(frozen=True)
class PairScore:
    writer_id: str
    payer_id: str
    score: DefensibilityScore


@dataclass(frozen=True)
class TriangularTournamentResult:
    writer_winner: WriterRef
    writer_losers: tuple[WriterRef, ...]
    payer_winner: PayerRef
    payer_losers: tuple[PayerRef, ...]
    all_pair_scores: tuple[PairScore, ...]

    @property
    def writer_winner_mean_defensibility(self) -> float:
        winner_id = self.writer_winner[0]
        scores = [
            ps.score.defensibility
            for ps in self.all_pair_scores
            if ps.writer_id == winner_id
        ]
        return statistics.mean(scores)

    @property
    def payer_winner_mean_inverse_defensibility(self) -> float:
        winner_id = self.payer_winner[0]
        inverses = [
            10 - ps.score.defensibility
            for ps in self.all_pair_scores
            if ps.payer_id == winner_id
        ]
        return statistics.mean(inverses)


class TriangularTournament:
    """Cross-product scoring of writer and payer candidate populations."""

    def __init__(
        self,
        *,
        payer_agent: PayerAgent,
        judge: DefensibilityJudge,
        gold: list[GoldAppeal],
    ) -> None:
        self._payer_agent = payer_agent
        self._judge = judge
        self._gold = gold

    async def run(
        self,
        *,
        writer_candidates: list[WriterRef],
        payer_candidates: list[PayerRef],
    ) -> TriangularTournamentResult:
        if not writer_candidates or not payer_candidates:
            raise ValueError(
                "triangular tournament requires at least one writer and one payer"
            )

        pairs: list[tuple[WriterRef, PayerRef]] = [
            (w, p) for w in writer_candidates for p in payer_candidates
        ]
        pair_scores = await asyncio.gather(
            *[self._score_pair(w, p) for w, p in pairs]
        )
        pair_scores_tuple = tuple(pair_scores)

        writer_ranking = self._rank_writers(writer_candidates, pair_scores_tuple)
        payer_ranking = self._rank_payers(payer_candidates, pair_scores_tuple)

        return TriangularTournamentResult(
            writer_winner=writer_ranking[0],
            writer_losers=tuple(writer_ranking[1:]),
            payer_winner=payer_ranking[0],
            payer_losers=tuple(payer_ranking[1:]),
            all_pair_scores=pair_scores_tuple,
        )

    async def _score_pair(
        self, writer: WriterRef, payer: PayerRef
    ) -> PairScore:
        _, _, writer_body = writer
        _, _, persona_id = payer
        denial = await self._payer_agent.deny(
            appeal=writer_body, persona_id=persona_id
        )
        score = await self._judge.score(
            candidate_appeal=writer_body,
            payer_denial_response=denial.denial_text,
            reference_set=self._gold,
        )
        return PairScore(writer_id=writer[0], payer_id=payer[0], score=score)

    @staticmethod
    def _rank_writers(
        writers: list[WriterRef], pair_scores: tuple[PairScore, ...]
    ) -> list[WriterRef]:
        def mean_def(w: WriterRef) -> float:
            return statistics.mean(
                ps.score.defensibility
                for ps in pair_scores
                if ps.writer_id == w[0]
            )

        return sorted(writers, key=lambda w: (-mean_def(w), w[0]))

    @staticmethod
    def _rank_payers(
        payers: list[PayerRef], pair_scores: tuple[PairScore, ...]
    ) -> list[PayerRef]:
        def mean_inv(p: PayerRef) -> float:
            return statistics.mean(
                10 - ps.score.defensibility
                for ps in pair_scores
                if ps.payer_id == p[0]
            )

        return sorted(payers, key=lambda p: (-mean_inv(p), p[0]))
