"""Run cross-cell transfer trials and write the TransferEdge artifact.

Clonal selection across cells: apply a source cell's champion STRATEGY (its evolved
system prompt) to the *target* cell's denials, judge the resulting appeals against
the target gold set, and record a transfer edge when the matured strategy
significantly lifts the target's naive baseline (one-tailed t-test p < 0.05 AND mean
composite >= baseline + 1.0). Pure evaluation — no Phoenix mutation.

The honesty: payer-specific citation *strings* do not carry over (negative selection
runs on the generated appeal against the TARGET cell's valid citations), but
transferable *structure* — quantified clinical metrics, section-level citation,
argument shape, deadline compliance — does. A lift means the strategy genuinely
writes better appeals in the new cell.

Usage:
    set -a; source .env; set +a
    env -u PYTHONPATH GRANUM_DATA_DIR=runs/cell_payloads uv run python scripts/run_transfer.py
Writes api_data/transfers.json.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from granum.center.judge import LLMJudge
from granum.data.denials import Denial, generate_denial
from granum.tools.gemini_client import GeminiClient
from granum.transfer.trial import TransferTrialHarness

DATA_DIR = Path(os.getenv("GRANUM_DATA_DIR", "runs/cell_payloads"))
OUT = Path("api_data/transfers.json")
N_SAMPLES = 5
SEED = 7
PAIRS = [
    ("aetna_cardiac", "united_oncology"),
    ("united_oncology", "aetna_cardiac"),
]


def _load_payload(cell: str) -> dict:
    return json.loads((DATA_DIR / f"{cell}.json").read_text())


def _champion(payload: dict) -> dict:
    champs = [s for s in payload["strategies"] if s["status"] == "champion"]
    if champs:
        return champs[0]
    return max(payload["strategies"], key=lambda s: s["fitness"])


def _baseline_composite(payload: dict) -> float:
    # Target's naive gen-0 baseline, on the judge's 0-10 composite scale.
    return float(payload["meta"]["baselineOverturn"]) * 10.0


def _rubric_path(cell: str) -> Path:
    p = Path(f"data/{cell}/judge_rubric.md")
    return p if p.exists() else Path("data/judge_rubric.md")


async def main() -> None:
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    gemini = GeminiClient()

    async def write_appeal(prompt_body: str, denial: Denial) -> str:
        # Transfer + adapt (somatic hypermutation): the matured STRATEGY carries
        # over, but its payer-specific citations are re-grounded to the target
        # payer — a clone selected for one antigen adapts its specifics to a new
        # one. The lift then measures whether the transferable structure (quantified
        # evidence, section-level citation, argument shape) genuinely helps here.
        payer = denial.payer.title()
        prompt = (
            f"{prompt_body}\n\n## Denial to appeal\n{denial.denial_text}\n\n"
            f"Payer: {denial.payer} | Diagnosis: {denial.diagnosis} | "
            f"CPT {denial.cpt_code} | ICD-10 {denial.icd10_code} | "
            f"Patient age {denial.patient_age_range} | "
            f"Appeal deadline {denial.appeal_deadline_days} days.\n\n"
            f"## Cross-cell adaptation\nThis strategy was matured against a different "
            f"payer. Apply its analytical rigor and structure, but cite {payer}'s OWN "
            f"controlling policies and guidelines — those referenced in this denial — "
            f"and never cite another payer's policy numbers.\n\n"
            "Write the complete appeal letter now. Output only the letter."
        )
        return await gemini.generate(model=model, prompt=prompt, temperature=0.3)

    edges: list[dict] = []
    for source, target in PAIRS:
        source_payload = _load_payload(source)
        target_payload = _load_payload(target)
        champ = _champion(source_payload)
        baseline = _baseline_composite(target_payload)
        target_payer, target_diagnosis = target.split("_", 1)

        harness = TransferTrialHarness(
            judge=LLMJudge(client=gemini, model=model, rubric_path=_rubric_path(target)),
            target_denial_factory=generate_denial,
            target_payer=target_payer,
            target_diagnosis=target_diagnosis,
            target_valid_citations_path=f"data/{target}/valid_citations.json",
            target_gold_path=f"data/{target}/gold_appeals.jsonl",
            baseline_target_fitness=baseline,
            appeal_generator=write_appeal,
        )
        trial = await harness.trial_transfer(
            source_cell=source,
            target_cell=target,
            prompt_id=champ["id"].split("__")[-1],
            prompt_version_id=champ["id"],
            prompt_body=champ["promptBody"],
            n_samples=N_SAMPLES,
            seed=SEED,
        )
        lift = trial.mean_score - trial.baseline_target_fitness
        promoted = trial.p_value < 0.05 and lift >= 1.0
        edges.append(
            {
                "sourceCell": source,
                "targetCell": target,
                "sourceStrategy": trial.prompt_id,
                "meanScore": round(trial.mean_score, 2),
                "baselineScore": round(trial.baseline_target_fitness, 2),
                "lift": round(lift, 2),
                "pValue": round(trial.p_value, 4),
                "samples": [round(s, 2) for s in trial.scores],
                "negativeSelectionFailures": trial.n_negative_selection_failures,
                "promoted": promoted,
            }
        )
        print(
            f"{source} -> {target}: mean={trial.mean_score:.2f} "
            f"baseline={trial.baseline_target_fitness:.2f} lift={lift:+.2f} "
            f"p={trial.p_value:.4f} ns_fail={trial.n_negative_selection_failures} "
            f"PROMOTED={promoted}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"edges": edges}, indent=2) + "\n")
    print(f"wrote {OUT} ({len(edges)} edges)")


if __name__ == "__main__":
    asyncio.run(main())
