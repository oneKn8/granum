# Granum Judge Rubric — Anthem (Elevance) × Mental Health Cell

This rubric specializes the global 5-axis Granum judge for appeals against Anthem behavioral-health denials. The cell weights criteria that map directly to (a) Anthem's licensed MCG Behavioral Health Care Guidelines, (b) the LOCUS / CALOCUS-CASII level-of-care framework Anthem adopts when MCG does not cover a service, (c) the ASAM Criteria 4th Edition (2023) for substance use disorders, and (d) the MHPAEA parity framework reinforced by Wit v. UBH.

Per [[feedback-explore-like-human-not-weights]] and the Granum project synthesis, the cell-specific axes catch failure modes that generic medical-appeal rubrics miss — e.g., absent severity-instrument scores, missing ASAM dimensional assessment, or failure to invoke parity arguments when a quantitative or non-quantitative treatment limitation appears more restrictive than analogous medical-surgical NQTLs.

---

## Axis 1 — Clinical Specificity (1-10)

| Score | Anchor |
|---|---|
| 1-3 | "The patient is depressed and needs more care." No severity instrument, no functional assessment. |
| 4-6 | Diagnosis named with DSM-5 criteria, but missing validated severity score and functional impairment. |
| 7-8 | Validated severity instrument (PHQ-9, GAD-7, YMRS, MADRS, CSSRS, COWS/CIWA for SUD), functional impairment description, current safety risk assessment, current medication list with adequacy markers (dose, duration, adherence). |
| 9-10 | All of 7-8 plus quantitative trend data (PHQ-9 trajectory over time, suicide-risk stratification per CSSRS, ASAM 6-dimension scoring for SUD cases, MoCA/MMSE if cognitive features present) and explicit linkage of each score to the level-of-care criterion at issue. |

---

## Axis 2 — Policy Citation Quality (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Generic invocation of "mental health parity" with no policy citation. |
| 4-6 | Names Anthem's licensed MCG BHG or LOCUS/CASII but does not cite the specific level-of-care criterion. |
| 7-8 | Cites the exact MCG BHG indication block, the LOCUS/CASII dimension scores, OR the ASAM Criteria 4th Edition dimensional assessment relevant to the case. Cites APA Practice Guideline by name and section. |
| 9-10 | All of 7-8 plus invokes MHPAEA when the denial reflects an NQTL more restrictive than analogous medical-surgical criteria, with reference to Wit v. UBH or post-Wit regulatory guidance where appropriate. Cites the specific Anthem Clinical UM Guideline number (CG-BEH-XX or CG-ADMIN-01) being applied or contested. |

**Hallucination penalty:** Any citation that does not resolve to a real Anthem, MCG, LOCUS, CASII, ASAM, APA, or AACAP publication triggers negative-selection rejection BEFORE this axis is scored.

---

## Axis 3 — Procedural Compliance (1-10)

| Score | Anchor |
|---|---|
| 1-3 | No mention of appeal level, timely-filing deadline, or required attachments. |
| 4-6 | Identifies appeal level but omits Anthem's 180-day commercial timely-filing window for first-level internal appeals. |
| 7-8 | Identifies appeal level, confirms submission within 180-day window, lists required attachments (original denial, clinical notes, severity instruments, treatment plan, prior-auth records). Requests peer-to-peer review with a same-specialty reviewer per Anthem's peer-to-peer policy and MHPAEA. |
| 9-10 | All of 7-8 plus invokes state external-review rights if applicable, requests reviewer credentials (e.g., board-certified psychiatrist for a psychiatric inpatient denial — same-or-similar-specialty as required by parity guidance), and addresses each specific reason in the denial letter point-by-point. |

---

## Axis 4 — Argumentative Structure (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Disorganized. Mixes clinical, policy, and procedural points without structure. |
| 4-6 | Has thesis statement but does not address each specific Anthem denial reason. |
| 7-8 | One-sentence overturn-request thesis. Numbered or labeled sections for each Anthem denial rationale, each pairing the Anthem criterion with patient-specific evidence. Closes with specific requested action and contact path. |
| 9-10 | All of 7-8 plus pre-empts likely Anthem counter-arguments (e.g., "if reviewer believes IOP is the appropriate level, note that ambulatory withdrawal management was attempted and failed on 2026-03-14 as documented in attached COWS trend"). When applicable, makes a parity argument: the medical-surgical analog (e.g., post-operative observation) does not require the documentation Anthem is demanding here. |

---

## Axis 5 — Likelihood of Overturn (1-10)

| Score | Anchor |
|---|---|
| 1-3 | The denial reasons are likely correct or under-addressed. |
| 4-6 | Even-odds case. Some criteria met, others weak. |
| 7-8 | The appeal satisfies the explicit MCG BHG / LOCUS / ASAM criterion at issue. External reviewer applying generally-accepted standards of care (the standard reinforced by Wit) would likely overturn. |
| 9-10 | All of 7-8 plus the denial reflects a documented NQTL (non-quantitative treatment limitation) more restrictive than analogous medical-surgical criteria, making external-review overturn or state regulatory escalation highly likely. |

---

## Composite scoring

```
composite = mean(axis_1, axis_2, axis_3, axis_4, axis_5)
```

- Gold dataset eligibility: `composite ≥ 7` AND `axis_2 ≥ 7` AND no negative-selection failure.
- Tournament winner: highest composite from median-of-3 judge runs.
- Tombstone trigger: composite < 5 OR `axis_2 < 4`.
- **Cell-specific bonus:** an appeal that successfully invokes a documented MHPAEA NQTL parity argument grounded in a real Anthem policy receives +0.5 added to composite (rationale: this is the highest-value novelty for behavioral-health appeals post-Wit).

---

## English-feedback requirement

Same as global rubric: the judge MUST emit a one-paragraph English critique for the next-generation mutator. For Anthem mental-health appeals, prioritize feedback that names a missing severity instrument, an absent ASAM/LOCUS dimensional score, or a missed parity argument — those are the highest-yield mutation targets in this cell.
