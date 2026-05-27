"""LLM-backed adversarial denial-writer for the Red Queen co-evolution loop.

In Phase 3, the deterministic synthetic denial generator in
`granum.data.denials.generate_denial` (a static pattern bank) is
augmented at runtime by a live LLM "payer reviewer" that reads an
in-flight candidate appeal and emits a denial response specifically
constructed to defeat that appeal. This module implements that agent.

The agent is parametrized by one of the seeded personas in
`granum.adversary.payer_persona`, which differ in tone and emphasis
but not in the structural contract: every produced denial must carry
a denial reason code, a policy citation, and an appeal-rights notice.
Structural enforcement of those three elements is handled downstream
by the negative-selection layer, not here.

This module is intentionally side-effect free with respect to the
synthetic pattern bank: callers may continue to use
`generate_denial` for cold-start corpus seeding and use `PayerAgent`
for adaptive co-evolution.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from granum.adversary.payer_persona import get_persona
from granum.data.denials import Denial, DenialReason


class _GenClient(Protocol):
    async def generate(
        self, *, model: str, prompt: str, temperature: float = 0.0
    ) -> str: ...


class PayerAgent:
    """Adversarial denial writer driven by a seeded payer persona.

    Constructed once per (payer, diagnosis) cell. The persona is
    selected per `deny()` call so a single agent instance can be
    rotated across personas during co-evolution rounds.
    """

    def __init__(
        self,
        *,
        client: _GenClient,
        model: str,
        payer: str,
        diagnosis: str,
    ) -> None:
        self._client = client
        self._model = model
        self._payer = payer
        self._diagnosis = diagnosis

    async def deny(self, *, appeal: str, persona_id: str) -> Denial:
        """Produce a persona-conditioned denial response to a candidate appeal.

        Raises:
            KeyError: if persona_id is not a seeded persona.
            ValueError: if the LLM returns a denial_reason not in the
                DenialReason enum (caller treats this as a regression).
            json.JSONDecodeError: if the LLM does not return valid JSON.
        """
        persona = get_persona(persona_id)
        prompt = self._build_prompt(persona.system_prompt, appeal)
        raw = await self._client.generate(
            model=self._model, prompt=prompt, temperature=0.0
        )
        parsed: dict[str, Any] = json.loads(raw)
        appeal_hash = hashlib.sha1(appeal.encode()).hexdigest()[:8]
        denial_id = (
            f"{self._payer}_{self._diagnosis}_adv_{persona_id}_{appeal_hash}"
        )
        return Denial(
            denial_id=denial_id,
            payer=self._payer,
            diagnosis=self._diagnosis,
            cpt_code=parsed["cpt_code"],
            icd10_code=parsed["icd10_code"],
            patient_age_range="adv",
            denial_reason=DenialReason(parsed["denial_reason"]),
            denial_text=parsed["denial_text"],
            submission_date="adversarial",
        )

    @staticmethod
    def _build_prompt(system_prompt: str, appeal: str) -> str:
        return (
            f"{system_prompt}\n\n"
            "## Candidate appeal to review\n"
            f"{appeal}\n\n"
            "## Output format\n"
            "Return ONLY valid JSON with these exact keys:\n"
            '  cpt_code (string, e.g. "93306"),\n'
            '  icd10_code (string, e.g. "I25.10"),\n'
            "  denial_reason (string, one of: not_medically_necessary | "
            "lacks_prior_auth | experimental_treatment | "
            "insufficient_clinical_documentation | step_therapy_required | "
            "duplicate_therapy | out_of_network),\n"
            "  denial_text (string, a full prose denial response 200-600 chars "
            "containing your reasoning, a policy citation, and an "
            "appeal-rights notice)."
        )
