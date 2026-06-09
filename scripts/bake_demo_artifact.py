"""Bake a curated, demo-ready CellPayload from a live evolve run artifact.

A finished ``granum evolve`` run spawns daughters on its final generation that
are never judged (no generation runs after them). They are honest as a live
"awaiting judge" frontier while the run grows on camera, but in a STATIC baked
artifact (what Cloud Run serves) they read as dangling fitness-0 nodes. This
script drops exactly that frontier and recomputes ``meta.populationSize`` so the
baked artifact represents the run's final *evaluated* population.

It is a pure JSON transform — no Phoenix/Vertex. The live artifact under
``runs/cell_payloads/`` is left untouched.

Usage:
    cd granum/
    env -u PYTHONPATH uv run python scripts/bake_demo_artifact.py \
        --src runs/cell_payloads/aetna_cardiac.json \
        --dest api_data/aetna_cardiac.json
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import typer

from granum.center.evolution import extract_citations, load_valid_citations

app = typer.Typer(help="Bake a curated demo CellPayload from a live run artifact.")


def _is_unjudged_frontier(strategy: dict, max_generation: int) -> bool:
    """A daughter spawned on the final generation that was never scored."""
    return (
        strategy["status"] != "tombstoned"
        and strategy["fitness"] == 0.0
        and strategy["generation"] == max_generation
        and strategy.get("parentId") is not None
    )


@app.command()
def bake(
    src: Path = typer.Option(..., "--src", help="Source live run artifact"),
    dest: Path = typer.Option(..., "--dest", help="Destination baked artifact"),
) -> None:
    payload = json.loads(src.read_text())
    strategies = payload["strategies"]
    max_generation = max(s["generation"] for s in strategies)

    kept = [s for s in strategies if not _is_unjudged_frontier(s, max_generation)]
    dropped = [s["id"] for s in strategies if s not in kept]

    # Re-derive citations with the cell-aware extractor: artifacts rendered
    # before extraction went cell-generic carry empty citations for non-aetna
    # cells even though the promptBody cites real policies.
    valid = load_valid_citations(payload["meta"]["id"])
    for s in kept:
        s["citations"] = extract_citations(s["promptBody"], valid)

    payload["strategies"] = kept
    payload["meta"]["populationSize"] = sum(
        1 for s in kept if s["status"] != "tombstoned"
    )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2))

    m = payload["meta"]
    typer.echo(f"dropped un-judged frontier: {dropped or 'none'}")
    typer.echo(
        f"baked {dest}: {m['baselineOverturn']} -> {m['currentOverturn']} | "
        f"gens={m['generations']} pop={m['populationSize']} "
        f"apoptosis={m['apoptosisTotal']} strategies={len(kept)}"
    )
    typer.echo(f"status counts: {dict(Counter(s['status'] for s in kept))}")
    cited = sum(1 for s in kept if s["citations"])
    typer.echo(f"strategies with citations: {cited}/{len(kept)}")


if __name__ == "__main__":
    app()
