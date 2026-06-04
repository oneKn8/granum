"""Tests for the self-improvement observability loop (Arize bonus criterion).

The agent writes a rich per-generation story to its Phoenix spans, then reads
that telemetry BACK (via get-spans) and lets the mutator optimize against the
weaknesses its own observability data reveals across generations.
"""
from granum.center.observability import (
    GenerationObservation,
    cycle_story_attributes,
    format_telemetry_digest,
    parse_generation_history,
)


def test_cycle_story_attributes_captures_the_self_improvement_story():
    attrs = cycle_story_attributes(
        cell="aetna_cardiac",
        generation=3,
        winner_id="g3m1",
        winner_fitness=8.4,
        population_size=3,
        apoptosis_ids=("bc2", "g2m0"),
        mutant_notes=(("g4m0", "tighter CPB citations"), ("g4m1", "added LVEF data")),
        rejected_count=1,
        critique="Appeal lacked section-level policy citations.",
    )
    # The trace must tell the story a judge can read in Phoenix.
    assert attrs["granum.cell"] == "aetna_cardiac"
    assert attrs["granum.generation"] == 3
    assert attrs["granum.winner_id"] == "g3m1"
    assert attrs["granum.winner_fitness"] == 8.4
    assert attrs["granum.population_size"] == 3
    assert attrs["granum.apoptosis_count"] == 2
    assert "bc2" in attrs["granum.apoptosis_ids"]
    assert attrs["granum.mutation_count"] == 2
    assert "tighter CPB citations" in attrs["granum.mutation_notes"]
    assert attrs["granum.negative_selection_rejected"] == 1
    assert "section-level" in attrs["granum.judge_critique"]
    # All attribute values must be OTel-legal scalars (str/int/float/bool).
    assert all(isinstance(v, (str, int, float, bool)) for v in attrs.values())


def test_judge_critique_attribute_is_truncated():
    attrs = cycle_story_attributes(
        cell="c", generation=0, winner_id="w", winner_fitness=5.0,
        population_size=1, apoptosis_ids=(), mutant_notes=(), rejected_count=0,
        critique="x" * 5000,
    )
    assert len(attrs["granum.judge_critique"]) <= 1000


def _span(name, *, generation, fitness, critique, start_time):
    return {
        "name": name,
        "start_time": start_time,
        "attributes": {
            "granum.cell": "aetna_cardiac",
            "granum.generation": generation,
            "granum.winner_fitness": fitness,
            "granum.judge_critique": critique,
        },
    }


def test_parse_generation_history_extracts_per_generation_sorted():
    spans = [
        _span("granum.cycle.aetna_cardiac", generation=1, fitness=5.4, critique="weak citations", start_time="2026-06-04T00:01:00Z"),
        _span("granum.cycle.aetna_cardiac", generation=0, fitness=4.0, critique="naive", start_time="2026-06-04T00:00:00Z"),
        _span("granum.cycle.tournament", generation=0, fitness=9.9, critique="noise", start_time="2026-06-04T00:00:30Z"),  # wrong span name → ignored
    ]
    hist = parse_generation_history(spans, cell="aetna_cardiac")
    assert [o.generation for o in hist] == [0, 1]  # sorted ascending
    assert hist[0].winner_fitness == 4.0
    assert hist[1].critique == "weak citations"


def test_parse_generation_history_dedups_keeping_latest_run_per_generation():
    # A prior --reset run left a stale gen-0 span; the newest one wins.
    spans = [
        _span("granum.cycle.aetna_cardiac", generation=0, fitness=2.0, critique="STALE old run", start_time="2026-06-01T00:00:00Z"),
        _span("granum.cycle.aetna_cardiac", generation=0, fitness=4.0, critique="FRESH this run", start_time="2026-06-04T00:00:00Z"),
    ]
    hist = parse_generation_history(spans, cell="aetna_cardiac")
    assert len(hist) == 1
    assert hist[0].critique == "FRESH this run"  # latest start_time kept


def test_parse_generation_history_filters_by_cell():
    spans = [
        _span("granum.cycle.aetna_cardiac", generation=0, fitness=4.0, critique="mine", start_time="t1"),
        _span("granum.cycle.united_oncology", generation=0, fitness=9.0, critique="other cell", start_time="t2"),
    ]
    hist = parse_generation_history(spans, cell="aetna_cardiac")
    assert len(hist) == 1
    assert hist[0].critique == "mine"


def test_format_telemetry_digest_summarizes_trend_and_critiques():
    history = [
        GenerationObservation(generation=0, winner_fitness=4.0, critique="lacks specific clinical evidence"),
        GenerationObservation(generation=1, winner_fitness=5.4, critique="citations not section-level"),
    ]
    digest = format_telemetry_digest(history)
    assert "2" in digest  # references the number of observed generations
    assert "0.40" in digest or "4.0" in digest  # the fitness trajectory
    assert "section-level" in digest  # carries the most recent observed weakness


def test_format_telemetry_digest_empty_is_safe():
    assert format_telemetry_digest([]) == ""
