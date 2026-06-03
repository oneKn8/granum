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
