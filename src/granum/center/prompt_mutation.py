"""Feedback-directed prompt mutation — the genuine self-improvement engine.

Mechanical citation-swaps make a strong baseline slightly WORSE, so the parent
wins every generation and nothing evolves. This mutator instead reads the judge's
English critique of the winning appeal and rewrites the B-cell STRATEGY (system
prompt) to fix the named weaknesses. That's directed optimization — daughters can
genuinely beat the parent — and it operationalizes Arize's "prompt learning from
feedback" thesis: the agent improves from English feedback, not from scalars.

Guardrails: the mutator is explicitly told NOT to fabricate citations/clinical
facts, and negative selection still tombstones any daughter that slips a
hallucinated citation through.
"""
from __future__ import annotations

import json
import os
from typing import Any, Awaitable, Callable, Protocol


def resolve_mutator_model(default_model: str) -> str:
    """Pick the model the writer mutator runs on.

    The mutator is the one place that genuinely needs a strong model: rewriting
    a whole strategy from English critique is what drives the fitness climb (the
    proven 0.40→0.98 arc used gemini-3.1-pro). The high-volume judge / payer /
    appeal-generation calls can stay on a cheap, fast model. ``GRANUM_MUTATOR_MODEL``
    lets the writer mutator use a stronger model than the rest of the run; unset
    or blank falls back to the run's main model.
    """
    override = os.getenv("GRANUM_MUTATOR_MODEL", "").strip()
    return override or default_model


class _GenClient(Protocol):
    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str: ...


_MUTATOR_PROMPT = """You improve an appeal-drafting STRATEGY — a SYSTEM PROMPT that \
instructs an LLM how to write prior-authorization appeal letters for patients denied \
medical care.

CURRENT STRATEGY:
\"\"\"
{parent}
\"\"\"

An expert appeals reviewer scored an appeal written with this strategy and gave this \
critique:
\"\"\"
{feedback}
\"\"\"

Write {n} IMPROVED variants of the STRATEGY that directly fix the weaknesses named in \
the critique while keeping what already works. Each variant MUST:
- be a complete, standalone system prompt (NOT a diff, NOT an appeal letter),
- make substantive, targeted improvements (e.g. demand more specific clinical evidence, \
exact policy-clause citations with section numbers, explicit procedural/deadline \
compliance, tighter argument structure),
- NEVER instruct the writer to fabricate citations, guidelines, or clinical facts,
- ALWAYS keep at least one real Aetna CPB citation (e.g. CPB 0119) and the 30-day /
  29 CFR 2560.503-1 appeal-deadline reference (these are required downstream),
- stay under 220 words.

Return ONLY a JSON array of exactly {n} objects, each:
{{"strategy": "<the full revised system prompt>", "change": "<<=8-word summary of what \
you improved>"}}"""


def _parse_variants(raw: str) -> list[dict[str, Any]]:
    """Parse the model's JSON array, tolerating ```json fences / prose."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    return data if isinstance(data, list) else []


def make_llm_mutator(
    *, client: _GenClient, model: str
) -> Callable[[str, str, int], Awaitable[list[tuple[str, str]]]]:
    """Build the cycle's `prompt_mutator`: (parent_body, feedback, n) -> [(body, note)]."""

    async def mutate(parent_body: str, feedback: str, n: int) -> list[tuple[str, str]]:
        prompt = _MUTATOR_PROMPT.format(
            parent=parent_body, feedback=feedback or "(no critique available)", n=n
        )
        # Higher temperature for variant diversity; JSON mode for a reliable parse.
        raw = await client.generate(
            model=model, prompt=prompt, temperature=0.8, json_mode=True
        )
        out: list[tuple[str, str]] = []
        for item in _parse_variants(raw):
            if not isinstance(item, dict):
                continue
            body = str(item.get("strategy", "")).strip()
            note = str(item.get("change", "")).strip() or "feedback-directed revision"
            if body:
                out.append((body, note))
        return out

    return mutate
