"""Generation-0 B-cell seed bank per (payer × diagnosis) cell.

Each seed is a system-prompt strategy for drafting an appeal. The three Aetna
baselines deliberately differ in citation density + tone so the gen-0 tournament
selects a meaningful winner. Shared by `scripts/seed_cell.py` and `granum evolve`.
"""
from __future__ import annotations

import asyncio

from granum.adversary.payer_persona import SEEDED_PERSONAS

# (name, body). Names use the logical `/` separator; PhoenixClient normalizes
# it to `__` (Phoenix strips `/`).
# Generation-0 seeds are deliberately NAIVE: each passes negative selection
# (it names a valid Aetna CPB + the 30-day deadline) but gives the writer no
# guidance on the things the judge rewards — quantified clinical values,
# section-level (§) citations, 29 CFR procedural framing, or argument structure.
# So gen-0 appeals score LOW, and feedback-directed evolution has to DISCOVER the
# expert strategy generation by generation. That is the real climb.
SEED_BANK: dict[str, list[tuple[str, str]]] = {
    "aetna_cardiac": [
        (
            "aetna_cardiac/bcell_1_generic",
            "You are writing a prior-authorization appeal letter for an Aetna "
            "cardiac coverage denial. Mention Aetna CPB 0119 and note the 30-day "
            "appeal deadline. Argue that the denial should be overturned because "
            "the care is medically necessary. Keep it under 500 words.",
        ),
        (
            "aetna_cardiac/bcell_2_persuasive",
            "Write a persuasive letter to Aetna appealing a denied cardiac "
            "procedure. Reference Aetna CPB 0119 and remind them of the 30-day "
            "deadline to file. Emphasize that the patient needs this treatment "
            "and that denying it is unreasonable.",
        ),
        (
            "aetna_cardiac/bcell_3_plain",
            "Draft a short appeal for an Aetna cardiac coverage denial. Cite "
            "Aetna CPB 0119 and state that the appeal must be filed within 30 "
            "days. Explain in plain language why the treatment is needed and ask "
            "Aetna to reconsider.",
        ),
    ],
    # Second cell. Same naive baselines: each names the controlling UnitedHealthcare
    # oncology policy and the appeal window, but offers no guidance on the things the
    # judge rewards (quantified prior-therapy records, section-level policy citations,
    # structured medical-necessity argument). So gen-0 scores low and has to climb.
    "united_oncology": [
        (
            "united_oncology/bcell_1_generic",
            "You are writing a prior-authorization appeal letter for a "
            "UnitedHealthcare oncology coverage denial. Mention the "
            "UnitedHealthcare Commercial Medical Drug Policy: Oncology Medication "
            "Clinical Coverage and note that the appeal must be filed before the "
            "deadline. Argue that the denial should be overturned because the "
            "treatment is medically necessary. Keep it under 500 words.",
        ),
        (
            "united_oncology/bcell_2_persuasive",
            "Write a persuasive letter to UnitedHealthcare appealing a denied "
            "oncology treatment. Reference the UnitedHealthcare Oncology Medication "
            "Clinical Coverage policy and remind them of the appeal deadline. "
            "Emphasize that the patient needs this treatment and that denying it "
            "is unreasonable.",
        ),
        (
            "united_oncology/bcell_3_plain",
            "Draft a short appeal for a UnitedHealthcare oncology coverage denial. "
            "Cite the UnitedHealthcare Commercial Medical Drug Policy for oncology "
            "medications and state that the appeal must be filed on time. Explain "
            "in plain language why the treatment is needed and ask UnitedHealthcare "
            "to reconsider.",
        ),
    ],
}


async def seed_cell(phoenix, *, cell: str) -> list[str]:
    """Seed a cell with its gen-0 B-cells (tagged production). No-op if already seeded.

    Returns the list of seeded prompt ids (empty if the cell already had active
    prompts).
    """
    seeds = SEED_BANK.get(cell)
    if not seeds:
        raise KeyError(f"No seed bank for cell {cell!r}. Have: {sorted(SEED_BANK)}")
    existing = await phoenix.list_active_prompts(name_prefix=f"{cell}/")
    if existing:
        return []
    ids: list[str] = []
    for name, body in seeds:
        pv = await phoenix.upsert_prompt(name=name, body=body, tags=("production",))
        ids.append(pv.prompt_id)
    return ids


async def seed_payers(phoenix, *, cell: str) -> list[str]:
    """Seed a cell's adversary population with gen-0 payer personas (tagged production).

    No-op if the cell already has active payer prompts.

    Returns the list of seeded prompt ids (empty if payer prompts already existed).
    """
    existing = await phoenix.list_active_prompts(name_prefix=f"{cell}_payer/")
    if existing:
        return []
    ids: list[str] = []
    for persona in SEEDED_PERSONAS:
        pv = await phoenix.upsert_prompt(
            name=f"{cell}_payer/baseline_{persona.persona_id}",
            body=persona.system_prompt,
            tags=("production",),
        )
        ids.append(pv.prompt_id)
    return ids


async def reset_cell(phoenix, *, cell: str) -> int:
    """Hard-delete every prompt under a cell so it can be re-seeded clean.

    Returns the count deleted. Demo-setup only (not apoptosis).
    """
    normalized = cell.replace("/", "__")
    deleted = 0
    for p in await phoenix.list_all_prompts():
        name = p.get("name", "")
        if name.startswith(normalized) and p.get("id"):
            await phoenix.delete_prompt(p["id"])
            deleted += 1
    return deleted


async def wait_for_active_population(
    phoenix,
    *,
    name_prefix: str,
    min_count: int = 1,
    attempts: int = 12,
    delay: float = 2.5,
) -> list:
    """Poll Phoenix until at least ``min_count`` active prompts are visible under ``name_prefix``.

    Guards against Phoenix Cloud eventual-consistency lag after seeding: a prompt
    upserted with the ``production`` tag may not be returned by
    ``list_active_prompts`` immediately.  Retries up to ``attempts`` times with
    ``delay`` seconds between polls.

    Returns the list of active prompts once the threshold is met.

    Raises ``RuntimeError`` if ``min_count`` prompts are not visible after all
    attempts are exhausted.
    """
    for attempt in range(attempts):
        prompts = await phoenix.list_active_prompts(name_prefix=name_prefix)
        if len(prompts) >= min_count:
            return prompts
        await asyncio.sleep(delay)
    raise RuntimeError(
        f"population under {name_prefix!r} did not reach {min_count} active prompt(s) "
        f"after {attempts} attempts"
    )
