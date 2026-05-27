"""LLM-as-judge with structured 5-axis rubric and median-of-3 sampling.

Per Arize CPO Aparna Dhinakaran's "prompt learning over scalar rewards"
thesis: the judge returns BOTH scalars (for selection arithmetic) AND
English feedback (for the next generation's mutator to read).

Median of 3 sampling at temperature=0 reduces stochasticity to a point
where downstream tournament rankings are stable across reruns.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from granum.data.gold import GoldAppeal


_DEFAULT_RUBRIC_PATH = Path("data/judge_rubric.md")


@dataclass(frozen=True)
class JudgeScore:
    clinical_specificity: int
    policy_citation_quality: int
    procedural_compliance: int
    argumentative_structure: int
    likelihood_overturn: int
    english_feedback: str

    @property
    def composite(self) -> float:
        return statistics.mean(
            [
                self.clinical_specificity,
                self.policy_citation_quality,
                self.procedural_compliance,
                self.argumentative_structure,
                self.likelihood_overturn,
            ]
        )


class _GenClient(Protocol):
    async def generate(
        self, *, model: str, prompt: str, temperature: float = 0.0
    ) -> str: ...


class LLMJudge:
    """Score candidate appeals against a gold reference set."""

    def __init__(
        self,
        *,
        client: _GenClient,
        model: str,
        rubric_path: Path = _DEFAULT_RUBRIC_PATH,
    ) -> None:
        self._client = client
        self._model = model
        # Read rubric lazily so absent file at import time doesn't crash
        self._rubric_path = rubric_path

    def _load_rubric(self) -> str:
        return self._rubric_path.read_text() if self._rubric_path.exists() else ""

    async def score(
        self, *, candidate_appeal: str, reference_set: list[GoldAppeal]
    ) -> JudgeScore:
        prompt = self._build_prompt(candidate_appeal, reference_set)
        # Three concurrent samples
        responses = await asyncio.gather(
            *[
                self._client.generate(
                    model=self._model, prompt=prompt, temperature=0.0
                )
                for _ in range(3)
            ]
        )
        parsed: list[dict[str, Any]] = [json.loads(r) for r in responses]
        return JudgeScore(
            clinical_specificity=int(
                statistics.median(p["clinical_specificity"] for p in parsed)
            ),
            policy_citation_quality=int(
                statistics.median(p["policy_citation_quality"] for p in parsed)
            ),
            procedural_compliance=int(
                statistics.median(p["procedural_compliance"] for p in parsed)
            ),
            argumentative_structure=int(
                statistics.median(p["argumentative_structure"] for p in parsed)
            ),
            likelihood_overturn=int(
                statistics.median(p["likelihood_overturn"] for p in parsed)
            ),
            english_feedback=parsed[0]["english_feedback"],
        )

    def _build_prompt(
        self, candidate: str, reference_set: list[GoldAppeal]
    ) -> str:
        rubric = self._load_rubric()
        refs = "\n\n".join(
            f"=== Reference (judge_score={r.judge_score}) ===\n{r.appeal_text}"
            for r in reference_set[:5]  # cap reference set to avoid prompt bloat
        )
        return (
            "You are a rigorous appeals reviewer. Score the candidate appeal "
            "on each of 5 axes (1-10) according to the rubric. Return ONLY JSON.\n\n"
            f"## Rubric\n{rubric}\n\n"
            f"## Reference appeals (overturned, gold-quality)\n{refs}\n\n"
            f"## Candidate appeal\n{candidate}\n\n"
            "Output JSON with keys: clinical_specificity, policy_citation_quality, "
            "procedural_compliance, argumentative_structure, likelihood_overturn, "
            "english_feedback (one-paragraph plain English critique, 200-400 chars)."
        )
