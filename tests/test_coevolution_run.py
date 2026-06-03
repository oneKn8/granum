"""Unit tests for CoEvolutionRun — mocked driver + phoenix (no live cost)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from granum.center.coevolution import CoEvolutionRoundResult
from granum.center.coevolution_run import CoEvolutionRun
from granum.tools.phoenix_client import PhoenixToolError


def _round(
    round_index,
    writer_scoreboard,
    payer_scoreboard,
    writer_winner_id,
    payer_winner_id,
    writer_loser_ids,
    payer_loser_ids,
    writer_mutant_ids,
    payer_mutant_ids,
    defensibility_composite=7.0,
    english_feedback="f",
):
    return CoEvolutionRoundResult(
        cell="aetna_cardiac",
        round_index=round_index,
        writer_winner_id=writer_winner_id,
        payer_winner_id=payer_winner_id,
        writer_loser_ids=tuple(writer_loser_ids),
        payer_loser_ids=tuple(payer_loser_ids),
        writer_mutant_ids=tuple(writer_mutant_ids),
        payer_mutant_ids=tuple(payer_mutant_ids),
        defensibility_composite=defensibility_composite,
        english_feedback=english_feedback,
        writer_scoreboard=tuple(writer_scoreboard),
        payer_scoreboard=tuple(payer_scoreboard),
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
async def test_run_accumulates_both_lineages_and_serializes_payload():
    driver = MagicMock()
    driver.round = AsyncMock(
        side_effect=[
            _round(
                round_index=0,
                writer_scoreboard=[("w1", 7.0), ("w2", 3.0)],
                payer_scoreboard=[("p1", 6.0), ("p2", 4.0)],
                writer_winner_id="w1",
                payer_winner_id="p1",
                writer_loser_ids=("w2",),
                payer_loser_ids=("p2",),
                writer_mutant_ids=("wm1",),
                payer_mutant_ids=("pm1",),
                defensibility_composite=7.0,
                english_feedback="f",
            ),
            _round(
                round_index=1,
                writer_scoreboard=[("w1", 8.0), ("wm1", 6.0)],
                payer_scoreboard=[("p1", 6.5), ("pm1", 5.0)],
                writer_winner_id="w1",
                payer_winner_id="p1",
                writer_loser_ids=(),
                payer_loser_ids=(),
                writer_mutant_ids=(),
                payer_mutant_ids=(),
                defensibility_composite=8.0,
                english_feedback="f2",
            ),
        ]
    )

    # w2 and p2 are tombstoned (losers); rest survive
    phoenix = _phoenix_with_sweep(dead_ids={"w2", "p2"})

    run = CoEvolutionRun(driver, phoenix, "aetna_cardiac", rounds=2)
    result = await run.run()
    payload = result.to_payload()

    # Top-level keys
    assert set(payload.keys()) == {"cell", "writers", "payers"}
    assert payload["cell"] == "aetna_cardiac"

    writers_by_id = {s["id"]: s for s in payload["writers"]}
    payers_by_id = {s["id"]: s for s in payload["payers"]}

    # All expected ids present
    assert set(writers_by_id.keys()) == {"w1", "w2", "wm1"}
    assert set(payers_by_id.keys()) == {"p1", "p2", "pm1"}

    # w1: max-fitness non-tombstoned writer → champion; fitness from round 1 = 8.0 → 0.8
    assert writers_by_id["w1"]["status"] == "champion"
    assert writers_by_id["w1"]["fitness"] == pytest.approx(0.8)

    # w2: tombstoned
    assert writers_by_id["w2"]["status"] == "tombstoned"

    # wm1: generation 1, parent w1
    assert writers_by_id["wm1"]["generation"] == 1
    assert writers_by_id["wm1"]["parentId"] == "w1"

    # p1: champion among payers
    assert payers_by_id["p1"]["status"] == "champion"

    # p2: tombstoned
    assert payers_by_id["p2"]["status"] == "tombstoned"

    # pm1: generation 1, parent p1
    assert payers_by_id["pm1"]["generation"] == 1
    assert payers_by_id["pm1"]["parentId"] == "p1"

    # All fitness values in [0, 1]
    for s in payload["writers"] + payload["payers"]:
        assert 0.0 <= s["fitness"] <= 1.0, f"{s['id']} fitness out of range: {s['fitness']}"

    # camelCase keys present in every strategy entry
    required_keys = {"id", "cell", "generation", "parentId", "label", "promptBody",
                     "mutationNote", "fitness", "tag", "status", "citations",
                     "createdAt", "killedAt"}
    for s in payload["writers"] + payload["payers"]:
        assert required_keys.issubset(s.keys()), f"missing keys in {s['id']}: {required_keys - s.keys()}"

    # killedAt: None for survivors, non-None for tombstoned
    assert writers_by_id["w1"]["killedAt"] is None
    assert writers_by_id["w2"]["killedAt"] is not None
    assert payers_by_id["p2"]["killedAt"] is not None
    assert payers_by_id["p1"]["killedAt"] is None
