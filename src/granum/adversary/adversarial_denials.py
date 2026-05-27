"""Adversarial denial factory — runtime replacement for the synthetic generator.

During Red Queen co-evolution (Phase 3), this LLM-driven factory replaces
`granum.data.denials.generate_denial` as the steady-state source of
denials feeding the immune-system evolution loop. The synthetic
pattern-bank generator continues to seed the cold-start corpus.

The factory rotates round-robin through the 5 SEEDED_PERSONAS to keep
selection pressure diverse (guards against the adversary collapsing
into a single failure mode). It rotates over a list of seed appeals
the same way, so that with N personas and M seed appeals the call
sequence covers N*M (persona, appeal) pairs before any pair repeats.

The sync adapter `as_denial_factory` adapts the async factory to the
synchronous `MultiCellDriver._DenialFactory` Protocol. It uses
`asyncio.run` and therefore MUST NOT be called from within an already
running event loop. Supporting that case is a v0.2 concern.
"""
from __future__ import annotations

import asyncio
from typing import Callable

from granum.adversary.payer_agent import PayerAgent
from granum.adversary.payer_persona import SEEDED_PERSONAS
from granum.data.denials import Denial


class AdversarialDenialFactory:
    """Round-robin denial generator using PayerAgent + the 5 SEEDED_PERSONAS.

    Replaces granum.data.denials.generate_denial at runtime during Red Queen
    co-evolution. The synthetic pattern-bank generator becomes the cold-start
    fallback; this LLM-driven factory becomes the steady-state denial source.

    State: maintains an internal index that increments each call; cycles
    through SEEDED_PERSONAS in declaration order (strict, lenient, formalist,
    cost_focused, evidence_focused, then back to strict).
    """

    def __init__(
        self,
        *,
        payer_agent: PayerAgent,
        seed_appeals: list[str],
    ) -> None:
        if not seed_appeals:
            raise ValueError("seed_appeals must not be empty")
        self._payer_agent = payer_agent
        self._seed_appeals = list(seed_appeals)
        self._next_index = 0

    async def generate(self) -> Denial:
        persona = SEEDED_PERSONAS[self._next_index % len(SEEDED_PERSONAS)]
        seed_appeal = self._seed_appeals[
            self._next_index % len(self._seed_appeals)
        ]
        denial = await self._payer_agent.deny(
            appeal=seed_appeal, persona_id=persona.persona_id
        )
        self._next_index += 1
        return denial


def as_denial_factory(
    *, payer_agent: PayerAgent, seed_appeals: list[str]
) -> Callable[..., Denial]:
    """Adapter making AdversarialDenialFactory compatible with MultiCellDriver._DenialFactory.

    The driver calls factory(payer=..., diagnosis=...) per-cell synchronously
    expecting an immediate Denial. We wrap an AdversarialDenialFactory and
    block on the async generate() call via asyncio.run.

    NOTE: asyncio.run cannot be called from within an already-running event
    loop. The driver runs synchronously today; supporting an async-context
    caller is a v0.2 concern.

    The (payer, diagnosis) kwargs are validated against the PayerAgent's
    own (payer, diagnosis) — a mismatch indicates the factory was bound
    to the wrong cell and is treated as a programming error.
    """
    if not seed_appeals:
        raise ValueError("seed_appeals must not be empty")
    factory = AdversarialDenialFactory(
        payer_agent=payer_agent, seed_appeals=seed_appeals
    )

    def _call(*, payer: str, diagnosis: str) -> Denial:
        if payer != payer_agent.payer or diagnosis != payer_agent.diagnosis:
            raise ValueError(
                f"adapter bound to ({payer_agent.payer!r}, "
                f"{payer_agent.diagnosis!r}) but called with "
                f"({payer!r}, {diagnosis!r})"
            )
        return asyncio.run(factory.generate())

    return _call
