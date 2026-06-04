"""Self-improvement observability loop — the Arize bonus criterion, for real.

Arize awards a bonus to agents that "use their own observability data to improve
over time." Granum closes that loop literally:

  1. Each germinal generation writes a rich STORY to its Phoenix span
     (``cycle_story_attributes``): winner, fitness, apoptosis, mutations, the
     judge's critique. The trace becomes a legible record of the climb.
  2. Before mutating, the agent reads its OWN prior-generation telemetry BACK
     from Phoenix (``get-spans`` → ``parse_generation_history``) and distills it
     into a digest (``format_telemetry_digest``) of the fitness trajectory and
     the weaknesses its observability data keeps surfacing.
  3. The mutator optimizes against that digest — so generation N+1 improves from
     accumulated telemetry, not just the last in-memory score.

The read-back is a real Phoenix MCP call visible in the trace; nothing here
fabricates data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_CRITIQUE_MAX = 1000


@dataclass(frozen=True)
class GenerationObservation:
    """One generation as read back from Phoenix telemetry."""

    generation: int
    winner_fitness: float  # 0-10 judge composite
    critique: str


def cycle_story_attributes(
    *,
    cell: str,
    generation: int,
    winner_id: str,
    winner_fitness: float,
    population_size: int,
    apoptosis_ids: tuple[str, ...],
    mutant_notes: tuple[tuple[str, str], ...],
    rejected_count: int,
    critique: str,
) -> dict[str, str | int | float | bool]:
    """Build the rich OTel span attributes that make a Phoenix trace tell the
    self-improvement story. All values are OTel-legal scalars (lists joined)."""
    return {
        "granum.cell": cell,
        "granum.generation": generation,
        "granum.winner_id": winner_id,
        "granum.winner_fitness": round(float(winner_fitness), 4),
        "granum.population_size": population_size,
        "granum.apoptosis_count": len(apoptosis_ids),
        "granum.apoptosis_ids": ",".join(apoptosis_ids),
        "granum.mutation_count": len(mutant_notes),
        "granum.mutation_notes": " | ".join(note for _, note in mutant_notes),
        "granum.negative_selection_rejected": rejected_count,
        "granum.judge_critique": (critique or "")[:_CRITIQUE_MAX],
    }


def parse_generation_history(
    spans: list[dict[str, Any]], *, cell: str
) -> list[GenerationObservation]:
    """Distil ``get-spans`` output into the cell's per-generation trajectory.

    Filters to this cell's top cycle spans (``granum.cycle.{cell}``), and when a
    prior ``--reset`` run left stale spans for the same generation, keeps the
    most recent one (latest ``start_time``). Returns ascending by generation.
    """
    target = f"granum.cycle.{cell}"
    latest: dict[int, tuple[Any, GenerationObservation]] = {}
    for span in spans:
        if span.get("name") != target:
            continue
        attrs = span.get("attributes") or {}
        gen = attrs.get("granum.generation")
        if gen is None:
            continue
        gen = int(gen)
        obs = GenerationObservation(
            generation=gen,
            winner_fitness=float(attrs.get("granum.winner_fitness", 0.0) or 0.0),
            critique=str(attrs.get("granum.judge_critique", "") or ""),
        )
        start = span.get("start_time", "")
        prev = latest.get(gen)
        if prev is None or start >= prev[0]:
            latest[gen] = (start, obs)
    return [latest[g][1] for g in sorted(latest)]


def format_telemetry_digest(history: list[GenerationObservation]) -> str:
    """Summarise the agent's own observed trajectory for the mutator.

    Empty history → empty string (gen 0, or a cold Phoenix read; caller falls
    back to the in-memory critique)."""
    if not history:
        return ""
    first, last = history[0], history[-1]
    delta = last.winner_fitness - first.winner_fitness
    lines = [
        f"## Your own Phoenix telemetry across {len(history)} prior generation(s)",
        (
            f"Champion appeal fitness moved {first.winner_fitness / 10:.2f} -> "
            f"{last.winner_fitness / 10:.2f} ({'+' if delta >= 0 else ''}{delta / 10:.2f})."
        ),
    ]
    if last.critique:
        lines.append(
            f"The most recent evaluation your telemetry recorded: \"{last.critique.strip()}\""
        )
    recent = [o.critique.strip() for o in history[-3:] if o.critique.strip()]
    if len(recent) > 1:
        lines.append(
            "Recurring weaknesses your observability data keeps surfacing across "
            "generations — fix the ones that persist:"
        )
        lines.extend(f"  - gen {o.generation}: {o.critique.strip()}" for o in history[-3:] if o.critique.strip())
    return "\n".join(lines)
