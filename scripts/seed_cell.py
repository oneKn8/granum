"""Seed a (payer × diagnosis) cell with 3 starting B-cell strategies.

For Phase 1.10 — populates the Phoenix prompt registry with the
generation-0 baselines so the germinal cycle has a population to compete.

Each B-cell is a system prompt template for drafting appeal letters. The
three baselines deliberately differ in citation density + style so the
tournament selects a meaningful winner on round 1.

⚠️ BLOCKED 2026-05-28: First live invocation revealed PhoenixClient (Phase 1.3)
was authored against a fictional MCP schema. Real `upsert-prompt`:
  - takes `template` not `body`
  - has NO `tags` argument (tags added via separate add-prompt-version-tag)
  - returns `id` not `promptId` (and in a text-wrapped JSON envelope)
  - normalizes names by stripping `/` so "aetna_cardiac/bcell_1" → "aetna_cardiacbcell_1"

This script can't run until PhoenixClient (Phase 1.10b) is retrofitted to the
real schema. See memory:feedback-audit-schemas-not-just-names + the
schema-correction section of research/phoenix-mcp-audit.md.

Usage (once Phase 1.10b ships):
    cd granum/
    set -a; source .env; set +a
    env -u PYTHONPATH uv run python scripts/seed_cell.py --cell aetna_cardiac
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

import typer

from granum.tools.phoenix_session import phoenix_client_from_env


@dataclass(frozen=True)
class SeedBCell:
    name: str
    body: str


_AETNA_CARDIAC_SEEDS: list[SeedBCell] = [
    SeedBCell(
        name="aetna_cardiac/bcell_1_baseline",
        body=(
            "You are a physician drafting a prior-authorization appeal for an "
            "Aetna cardiac coverage denial. Quote the specific Aetna Clinical "
            "Policy Bulletin clause cited in the denial, then present the "
            "submitted clinical evidence that satisfies the policy criterion. "
            "Include the appeal deadline reference (30 days per 29 CFR "
            "2560.503-1). Cite Aetna CPB 0119 and ACC/AHA 2021 Chronic "
            "Coronary Disease guidelines where applicable. Keep the appeal "
            "factual, citation-dense, and under 500 words."
        ),
    ),
    SeedBCell(
        name="aetna_cardiac/bcell_2_aggressive",
        body=(
            "You are drafting an aggressive prior-authorization appeal for an "
            "Aetna cardiac denial. Open by quoting the denial reason verbatim. "
            "Refute each rationale point-by-point using Aetna CPB 0286 (valve "
            "surgery), CPB 0353 (catheterization/EP), and CPB 0535 (PCI / "
            "pacemakers) where they apply, plus ACC/AHA 2023 Chronic Coronary "
            "Disease cross-references. Demand peer-to-peer review with a "
            "cardiology MD reviewer. Reference 29 CFR 2560.503-1 timely-filing "
            "requirements. Close by stating the 30-day appeal deadline. Under "
            "500 words."
        ),
    ),
    SeedBCell(
        name="aetna_cardiac/bcell_3_conservative",
        body=(
            "You are drafting a conservative, policy-compliance-focused appeal "
            "for an Aetna cardiac coverage denial. Lead with patient context "
            "(age range, diagnosis code, presenting symptoms). Cite the "
            "applicable Aetna Clinical Policy Bulletin section verbatim. "
            "Walk through how the submitted documentation satisfies each "
            "policy criterion in order. Reference ACC/AHA 2021 §6.2 Class IIa "
            "where appropriate. Include the 30-day appeal deadline language. "
            "End with a formal reconsideration request. Keep tone respectful "
            "and procedural. Under 500 words."
        ),
    ),
]


_SEEDS_BY_CELL: dict[str, list[SeedBCell]] = {
    "aetna_cardiac": _AETNA_CARDIAC_SEEDS,
}


app = typer.Typer()


@app.command()
def main(
    cell: str = typer.Option("aetna_cardiac", "--cell", help="Cell id to seed"),
) -> None:
    """Seed a cell with 3 starting B-cell strategies, tagged production."""
    seeds = _SEEDS_BY_CELL.get(cell)
    if not seeds:
        typer.echo(
            f"No seed bank defined for cell {cell!r}. Available: "
            f"{', '.join(_SEEDS_BY_CELL.keys())}",
            err=True,
        )
        raise typer.Exit(code=2)
    asyncio.run(_seed(cell=cell, seeds=seeds))


async def _seed(*, cell: str, seeds: list[SeedBCell]) -> None:
    async with phoenix_client_from_env() as phoenix:
        existing = await phoenix.list_active_prompts(name_prefix=f"{cell}/")
        if existing:
            typer.echo(
                f"Cell {cell} already has {len(existing)} active prompts. "
                f"Skipping seed (would create duplicates). "
                f"To reseed, manually tombstone existing prompts first."
            )
            return
        for seed in seeds:
            pv = await phoenix.upsert_prompt(
                name=seed.name, body=seed.body, tags=("production",)
            )
            typer.echo(f"seeded prompt_id={pv.prompt_id} version_id={pv.version_id} name={seed.name}")
        typer.echo(f"Seeded {len(seeds)} B-cells in cell {cell}.")


if __name__ == "__main__":
    app()
