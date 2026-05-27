"""Transfer trial harness — N-sample evaluation of a source-cell strategy
in a target-cell denial environment.

Output is a TransferTrial with per-sample composite scores + a one-sample
t-test p-value vs the target cell's baseline mean fitness. Task 4.3
(promote_transfer) gates on TransferTrial.p_value < 0.05 AND
mean_score >= baseline + 1.0.

The harness does NOT mutate Phoenix state — it's pure evaluation. The
promotion step (Task 4.3) is where the source strategy gets upserted
into the target cell namespace.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from granum.center.judge import LLMJudge
from granum.center.negative_selection import verify_citations
from granum.data.denials import Denial
from granum.data.gold import GoldAppeal, load_gold_appeals


class _DenialFactory(Protocol):
    def __call__(
        self, *, payer: str, diagnosis: str, seed: int | None = ...
    ) -> Denial: ...


@dataclass(frozen=True)
class TransferTrial:
    source_cell: str
    target_cell: str
    prompt_id: str
    prompt_version_id: str
    prompt_body: str
    scores: tuple[float, ...]
    mean_score: float
    p_value: float
    baseline_target_fitness: float
    n_negative_selection_failures: int = 0


class TransferTrialHarness:
    def __init__(
        self,
        *,
        judge: LLMJudge,
        target_denial_factory: _DenialFactory,
        target_payer: str,
        target_diagnosis: str,
        target_valid_citations_path: str | Path,
        target_gold_path: str | Path,
        baseline_target_fitness: float,
    ) -> None:
        self._judge = judge
        self._denial_factory = target_denial_factory
        self._target_payer = target_payer
        self._target_diagnosis = target_diagnosis
        self._valid_citations_path = target_valid_citations_path
        self._gold: list[GoldAppeal] = load_gold_appeals(target_gold_path)
        self._baseline = baseline_target_fitness

    async def trial_transfer(
        self,
        *,
        source_cell: str,
        target_cell: str,
        prompt_id: str,
        prompt_version_id: str,
        prompt_body: str,
        n_samples: int = 5,
        seed: int = 0,
    ) -> TransferTrial:
        """Evaluate a source-cell prompt against n_samples target-cell denials."""
        if n_samples < 2:
            raise ValueError("trial_transfer requires n_samples >= 2 for t-test")

        # 1. Negative selection against the TARGET cell's valid-citation set.
        ns_result = verify_citations(
            prompt_body, valid_set_path=self._valid_citations_path
        )
        if not ns_result.passed:
            return TransferTrial(
                source_cell=source_cell,
                target_cell=target_cell,
                prompt_id=prompt_id,
                prompt_version_id=prompt_version_id,
                prompt_body=prompt_body,
                scores=(0.0,) * n_samples,
                mean_score=0.0,
                p_value=1.0,
                baseline_target_fitness=self._baseline,
                n_negative_selection_failures=n_samples,
            )

        # 2. Per-sample target-cell denial generation + judge scoring.
        scores: list[float] = []
        for i in range(n_samples):
            _ = self._denial_factory(
                payer=self._target_payer,
                diagnosis=self._target_diagnosis,
                seed=seed + i,
            )
            judge_score = await self._judge.score(
                candidate_appeal=prompt_body,
                reference_set=self._gold,
            )
            scores.append(judge_score.composite)

        # 3. One-sample t-test vs baseline (one-tailed: mean > baseline).
        mean = statistics.mean(scores)
        stdev = statistics.stdev(scores) if n_samples >= 2 else 0.0
        if stdev == 0.0:
            p_value = 0.0 if mean > self._baseline else 1.0
        else:
            t = (mean - self._baseline) / (stdev / math.sqrt(n_samples))
            df = n_samples - 1
            p_value = _t_survival(t, df)

        return TransferTrial(
            source_cell=source_cell,
            target_cell=target_cell,
            prompt_id=prompt_id,
            prompt_version_id=prompt_version_id,
            prompt_body=prompt_body,
            scores=tuple(scores),
            mean_score=mean,
            p_value=p_value,
            baseline_target_fitness=self._baseline,
            n_negative_selection_failures=0,
        )


def _t_survival(t: float, df: int) -> float:
    """One-tailed survival of Student's t — P(T > t).

    Normal approximation valid for df >= 4 (n_samples >= 5 in practice).
    """
    if t <= 0:
        return 1.0 - _norm_cdf(t)
    denom = df + t * t - 1
    adj_t = t * math.sqrt(df / denom) if denom > 0 else t
    return 1.0 - _norm_cdf(adj_t)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
