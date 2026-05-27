"""Defensibility judge — scores appeals against adversarial payer denials.

Used by TriangularTournament (Task 3.4) in Red Queen co-evolution. Differs
from LLMJudge in:
- Takes 3 inputs: appeal, payer_denial_response, gold reference set
- Returns DefensibilityScore where the 5th axis is "defensibility" (how well
  the appeal pre-empts the payer's specific denial), not "likelihood_overturn"
- Otherwise mirrors LLMJudge: median-of-3 sampling at temp=0, English feedback
"""
from __future__ import annotations

import asyncio
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from granum.data.gold import GoldAppeal


_DEFAULT_RUBRIC_PATH = Path("data/defensibility_rubric.md")


@dataclass(frozen=True)
class DefensibilityScore:
    clinical_specificity: int
    policy_citation_quality: int
    procedural_compliance: int
    argumentative_structure: int
    defensibility: int
    english_feedback: str

    @property
    def composite(self) -> float:
        return statistics.mean(
            [
                self.clinical_specificity,
                self.policy_citation_quality,
                self.procedural_compliance,
                self.argumentative_structure,
                self.defensibility,
            ]
        )


class _GenClient(Protocol):
    async def generate(
        self, *, model: str, prompt: str, temperature: float = 0.0
    ) -> str: ...


class DefensibilityJudge:
    """Score candidate appeals against a specific payer denial response."""

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
        self,
        *,
        candidate_appeal: str,
        payer_denial_response: str,
        reference_set: list[GoldAppeal],
    ) -> DefensibilityScore:
        prompt = self._build_prompt(
            candidate_appeal, payer_denial_response, reference_set
        )
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
        return DefensibilityScore(
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
            defensibility=int(
                statistics.median(p["defensibility"] for p in parsed)
            ),
            english_feedback=parsed[0]["english_feedback"],
        )

    def _build_prompt(
        self,
        candidate_appeal: str,
        payer_denial_response: str,
        reference_set: list[GoldAppeal],
    ) -> str:
        rubric = self._load_rubric()
        refs = "\n\n".join(
            f"=== Reference (judge_score={r.judge_score}) ===\n{r.appeal_text}"
            for r in reference_set[:5]  # cap reference set to avoid prompt bloat
        )
        return (
            "You are a rigorous appeals reviewer evaluating whether a candidate "
            "appeal successfully withstands a payer's denial response. Score on "
            "each of 5 axes (1-10) according to the rubric. Return ONLY JSON.\n\n"
            f"## Rubric\n{rubric}\n\n"
            f"## Reference appeals (overturned, gold-quality)\n{refs}\n\n"
            f"## Payer denial response (adversary)\n{payer_denial_response}\n\n"
            f"## Candidate appeal (to be defended)\n{candidate_appeal}\n\n"
            "Output JSON with keys: clinical_specificity, policy_citation_quality, "
            "procedural_compliance, argumentative_structure, defensibility, "
            "english_feedback (one-paragraph plain English critique, 200-400 chars)."
        )
