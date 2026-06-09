"""Unit tests for GenerationalEvolution — mocked cycle + phoenix (no live cost)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.center.cycle import CycleOutcome
from granum.center.evolution import GenerationalEvolution
from granum.data.denials import generate_denial
from granum.tools.phoenix_client import PhoenixToolError


def _outcome(gen, scoreboard, winner, tombstoned, mutants, notes):
    return CycleOutcome(
        cell="aetna_cardiac",
        denial_id="d1",
        survivors_before_tournament=tuple(i for i, _ in scoreboard),
        rejected_by_negative_selection=(),
        winner_id=winner,
        winner_version_id="v",
        winner_composite_score=dict(scoreboard)[winner],
        tombstoned_ids=tombstoned,
        mutant_ids=mutants,
        winner_appeal=f"appeal for {winner}",
        english_feedback="fb",
        scoreboard=tuple(scoreboard),
        mutant_notes=tuple(notes),
        generation=gen,
    )


def _phoenix_with_sweep(dead_ids: set[str]) -> MagicMock:
    phoenix = MagicMock()

    async def call_tool(name, args):
        ident, tag = args["prompt_identifier"], args["tag_name"]
        if tag == "production" and ident in dead_ids:
            raise PhoenixToolError("404")
        if tag == "tombstoned" and ident not in dead_ids:
            raise PhoenixToolError("404")
        return {"id": "vX", "template": "body of " + ident}

    phoenix._mcp.call_tool = AsyncMock(side_effect=call_tool)
    return phoenix


@pytest.mark.asyncio
async def test_evolution_chains_generations_and_builds_lineage():
    cycle = MagicMock()
    cycle.run = AsyncMock(
        side_effect=[
            _outcome(
                0, [("bc1", 8.0), ("bc2", 6.0), ("bc3", 7.0)], "bc1",
                ("bc2", "bc3"), ("g1m0",), [("g1m0", "citation_swap: A → B")],
            ),
            _outcome(
                1, [("bc1", 8.0), ("g1m0", 8.5)], "g1m0",
                ("bc1",), ("g2m0",), [("g2m0", "paragraph_reframe: x → y")],
            ),
        ]
    )
    phoenix = _phoenix_with_sweep(dead_ids={"bc1", "bc2", "bc3"})
    ev = GenerationalEvolution(
        cycle=cycle, phoenix=phoenix, cell="aetna_cardiac", generations=2
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)

    result = await ev.run(denial=denial)

    # chained 2 generations, passing generation=0 then 1
    assert cycle.run.await_count == 2
    assert [c.kwargs["generation"] for c in cycle.run.await_args_list] == [0, 1]

    by_id = {s.id: s for s in result.strategies}
    assert by_id["bc1"].parent_id is None and by_id["bc1"].generation == 0
    assert by_id["g1m0"].parent_id == "bc1" and by_id["g1m0"].generation == 1
    assert by_id["g2m0"].parent_id == "g1m0" and by_id["g2m0"].generation == 2
    # sweep set status from Phoenix
    assert by_id["bc2"].status == "tombstoned"
    assert by_id["g1m0"].status == "production"
    assert by_id["g1m0"].body == "body of g1m0"
    assert by_id["g1m0"].mutation_note.startswith("citation_swap")


@pytest.mark.asyncio
async def test_evolution_fitness_curve_and_payload():
    cycle = MagicMock()
    cycle.run = AsyncMock(
        side_effect=[
            _outcome(
                0, [("bc1", 6.0), ("bc2", 7.0), ("bc3", 8.0)], "bc3",
                ("bc1", "bc2"), ("g1m0",), [("g1m0", "citation_swap: A → B")],
            ),
            _outcome(
                1, [("bc3", 8.0), ("g1m0", 9.0)], "g1m0",
                ("bc3",), (), [],
            ),
        ]
    )
    phoenix = _phoenix_with_sweep(dead_ids={"bc1", "bc2", "bc3"})
    ev = GenerationalEvolution(
        cycle=cycle, phoenix=phoenix, cell="aetna_cardiac", generations=2
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)

    result = await ev.run(denial=denial)
    fc = result.fitness_curve()

    assert [p["generation"] for p in fc] == [0, 1]
    assert fc[0]["maxFitness"] == 0.8  # 8.0 / 10
    assert fc[1]["maxFitness"] == 0.9  # fitness climbed
    assert fc[0]["apoptosisCount"] == 2
    assert fc[1]["apoptosisCount"] == 1

    payload = result.to_payload()
    assert payload["meta"]["id"] == "aetna_cardiac"
    assert payload["meta"]["generations"] == 2
    assert payload["meta"]["apoptosisTotal"] == 3
    assert {s["id"] for s in payload["strategies"]} == {"bc1", "bc2", "bc3", "g1m0"}
    assert len(payload["rounds"]) == 2
    assert payload["rounds"][1]["winnerId"] == "g1m0"
    # production survivors only counted in populationSize
    assert payload["meta"]["populationSize"] == 1  # only g1m0 production


@pytest.mark.asyncio
async def test_progress_sink_called_after_each_generation_with_growing_payload():
    """Live-grow: the runner emits a partial payload after EACH generation so a
    polling API serves more generations over time. Losers are tombstoned
    incrementally so deaths show up live, not only after the final sweep."""
    cycle = MagicMock()
    cycle.run = AsyncMock(
        side_effect=[
            _outcome(
                0, [("bc1", 8.0), ("bc2", 6.0), ("bc3", 7.0)], "bc1",
                ("bc2", "bc3"), ("g1m0",), [("g1m0", "citation_swap: A → B")],
            ),
            _outcome(
                1, [("bc1", 8.0), ("g1m0", 8.5)], "g1m0",
                ("bc1",), ("g2m0",), [("g2m0", "reframe: x → y")],
            ),
        ]
    )
    phoenix = _phoenix_with_sweep(dead_ids={"bc1", "bc2", "bc3"})
    ev = GenerationalEvolution(
        cycle=cycle, phoenix=phoenix, cell="aetna_cardiac", generations=2
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)

    snapshots: list[dict] = []
    await ev.run(denial=denial, progress_sink=lambda r: snapshots.append(r.to_payload()))

    # One snapshot per generation, generation count grows.
    assert len(snapshots) == 2
    assert snapshots[0]["meta"]["generations"] == 1
    assert snapshots[1]["meta"]["generations"] == 2
    # Incremental apoptosis: gen-0 losers are tombstoned in the gen-0 snapshot
    # (before the final Phoenix sweep ran).
    g0 = {s["id"]: s for s in snapshots[0]["strategies"]}
    assert g0["bc2"]["status"] == "tombstoned"
    assert g0["bc3"]["status"] == "tombstoned"


@pytest.mark.asyncio
async def test_current_overturn_is_champion_fitness_not_peak():
    """meta.currentOverturn must equal the champion's LATEST fitness (what the FE
    pill shows), not the run's peak — they diverge when the champion dips after a
    peak. baselineOverturn stays the gen-0 best."""
    cycle = MagicMock()
    cycle.run = AsyncMock(
        side_effect=[
            _outcome(0, [("bc1", 4.0)], "bc1", (), (), []),   # baseline
            _outcome(1, [("bc1", 9.8)], "bc1", (), (), []),   # peak
            _outcome(2, [("bc1", 9.6)], "bc1", (), (), []),   # champion's final
        ]
    )
    phoenix = _phoenix_with_sweep(dead_ids=set())
    ev = GenerationalEvolution(
        cycle=cycle, phoenix=phoenix, cell="aetna_cardiac", generations=3
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)

    payload = (await ev.run(denial=denial)).to_payload()

    assert payload["meta"]["baselineOverturn"] == 0.4   # gen-0 best
    assert payload["meta"]["currentOverturn"] == 0.96   # champion's latest, NOT 0.98 peak


def test_extract_citations_regex_only_without_valid_set():
    from granum.center.evolution import extract_citations

    body = "Cite Aetna CPB 0119 and the 29 CFR 2560.503-1 deadline."
    assert extract_citations(body) == ["29 CFR 2560.503-1", "Aetna CPB 0119"]


def test_extract_citations_is_cell_generic_via_valid_set():
    """Non-aetna cells get real citations from their own valid_citations.json
    (the Aetna/ACC/CFR regexes can never match UHC policy names)."""
    from granum.center.evolution import extract_citations, load_valid_citations

    valid = load_valid_citations("united_oncology")
    assert valid, "united_oncology valid_citations.json should load"
    body = (
        "Reference the UnitedHealthcare Commercial Medical Drug Policy: "
        "Oncology Medication Clinical Coverage and file within the 65-day window."
    )
    cites = extract_citations(body, valid)
    assert (
        "UnitedHealthcare Commercial Medical Drug Policy: "
        "Oncology Medication Clinical Coverage" in cites
    )


def test_load_valid_citations_none_for_unknown_cell():
    from granum.center.evolution import load_valid_citations

    assert load_valid_citations("no_such_cell") is None
