"""Generation-0 B-cell seed bank per (payer × diagnosis) cell.

Each seed is a system-prompt strategy for drafting an appeal. The three Aetna
baselines deliberately differ in citation density + tone so the gen-0 tournament
selects a meaningful winner. Shared by `scripts/seed_cell.py` and `granum evolve`.
"""
from __future__ import annotations

# (name, body). Names use the logical `/` separator; PhoenixClient normalizes
# it to `__` (Phoenix strips `/`).
SEED_BANK: dict[str, list[tuple[str, str]]] = {
    "aetna_cardiac": [
        (
            "aetna_cardiac/bcell_1_baseline",
            "You are a physician drafting a prior-authorization appeal for an "
            "Aetna cardiac coverage denial. Quote the specific Aetna Clinical "
            "Policy Bulletin clause cited in the denial, then present the "
            "submitted clinical evidence that satisfies the policy criterion. "
            "Include the appeal deadline reference (30 days per 29 CFR "
            "2560.503-1). Cite Aetna CPB 0119 and ACC/AHA 2021 Chronic "
            "Coronary Disease guidelines where applicable. Keep the appeal "
            "factual, citation-dense, and under 500 words.",
        ),
        (
            "aetna_cardiac/bcell_2_aggressive",
            "You are drafting an aggressive prior-authorization appeal for an "
            "Aetna cardiac denial. Open by quoting the denial reason verbatim. "
            "Refute each rationale point-by-point using Aetna CPB 0286 (valve "
            "surgery), CPB 0353 (catheterization/EP), and CPB 0535 (PCI / "
            "pacemakers) where they apply, plus ACC/AHA 2023 Chronic Coronary "
            "Disease cross-references. Demand peer-to-peer review with a "
            "cardiology MD reviewer. Reference 29 CFR 2560.503-1 timely-filing "
            "requirements. Close by stating the 30-day appeal deadline. Under "
            "500 words.",
        ),
        (
            "aetna_cardiac/bcell_3_conservative",
            "You are drafting a conservative, policy-compliance-focused appeal "
            "for an Aetna cardiac coverage denial. Lead with patient context "
            "(age range, diagnosis code, presenting symptoms). Cite the "
            "applicable Aetna Clinical Policy Bulletin section verbatim. "
            "Walk through how the submitted documentation satisfies each "
            "policy criterion in order. Reference ACC/AHA 2021 §6.2 Class IIa "
            "where appropriate. Include the 30-day appeal deadline language. "
            "End with a formal reconsideration request. Keep tone respectful "
            "and procedural. Under 500 words.",
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
