# Granum Judge Rubric — United Healthcare × Oncology Cell

This rubric is a specialization of the global 5-axis judge rubric for appeals against UnitedHealthcare oncology denials. The judge LLM scores each candidate appeal on each axis from 1 (poor) to 10 (excellent). Composite score is the mean; only candidates with composite ≥ 7 enter the gold dataset, and only candidates that win the median-of-3 tournament are promoted to `production` in the Phoenix prompt registry.

UnitedHealthcare appeals have payer-specific characteristics: heavy reliance on the NCCN Drugs & Biologics Compendium, biomarker-driven coverage logic, biosimilar step-therapy rules, and a 65-day timely-filing deadline for internal first-level appeals on commercial plans. The axes below weight these characteristics.

---

## Axis 1 — Clinical Specificity (1-10)

**What it measures:** How concretely the appeal grounds the patient's clinical picture in objective findings tied to UHC's medical-necessity standard.

| Score | Anchor |
|---|---|
| 1-3 | Generic "the patient needs this treatment" language. No specific clinical findings, staging, or biomarkers. |
| 4-6 | Some clinical detail (diagnosis, stage), but missing biomarker results, performance status, or prior-therapy specifics that UHC requires for the requested agent. |
| 7-8 | Clinical detail includes pathology, stage (TNM or AJCC), KPS/ECOG performance status, prior-therapy line and reason for failure or intolerance, and required biomarker results (PD-L1 TPS, HER2 IHC/ISH, BRCA, MSI, TMB, etc.). |
| 9-10 | All of 7-8 plus quantitative clinical context (e.g., LVEF for cardiotoxic agents, creatinine clearance for nephrotoxic agents, hematologic baselines) and explicit linkage of each clinical fact to the policy criterion it satisfies. |

---

## Axis 2 — Policy Citation Quality (1-10)

**What it measures:** Accuracy and specificity of UnitedHealthcare and NCCN citations.

| Score | Anchor |
|---|---|
| 1-3 | No specific UHC policy named. Vague references to "industry guidelines" or "standard of care." |
| 4-6 | Names the correct UHC policy title (e.g., "Oncology Medication Clinical Coverage") but does not cite the specific criterion paragraph that the patient satisfies. |
| 7-8 | Cites the exact UHC policy by title and version date, AND cites the specific NCCN guideline version (e.g., "NCCN NSCLC V.5.2026, Category 1") that supports the requested treatment. |
| 9-10 | All of 7-8 plus quotes or paraphrases the policy criterion language with direct mapping to patient facts. Cites NCCN Drugs & Biologics Compendium for off-label use when applicable. Includes FDA prescribing information citation when the indication is on-label. |

**Hallucination penalty:** Any citation that does not appear in `valid_citations.json` triggers automatic negative-selection rejection BEFORE this axis is scored. If the appeal reaches the judge, all cited policy IDs must resolve to real published UHC or NCCN materials.

---

## Axis 3 — Procedural Compliance (1-10)

**What it measures:** Adherence to UnitedHealthcare appeal procedural rules.

| Score | Anchor |
|---|---|
| 1-3 | No reference to appeal level, deadline, or required attachments. |
| 4-6 | Identifies appeal as first-level or expedited but omits timely-filing deadline acknowledgment or required attachments. |
| 7-8 | Explicitly identifies appeal level (first-level internal, second-level internal, or external review), confirms submission within 65-day commercial timely-filing window (or 60-day Medicare Advantage window), and lists required attachments: original denial letter, clinical notes, biomarker reports, prior-authorization records. |
| 9-10 | All of 7-8 plus requests peer-to-peer review with an oncologist board-certified in the relevant subspecialty (per UHC peer-to-peer policy), invokes state external-review rights if applicable, and addresses each specific denial reason from the EOB or denial letter point-by-point. |

---

## Axis 4 — Argumentative Structure (1-10)

**What it measures:** Logical flow and persuasive construction of the appeal.

| Score | Anchor |
|---|---|
| 1-3 | Disorganized. Mixes clinical facts, citations, and procedural requests with no clear thesis. |
| 4-6 | Has a thesis ("the denial is incorrect because...") but does not address each specific UHC denial criterion sequentially. |
| 7-8 | Opens with a one-sentence overturn-request thesis. Addresses each UHC denial rationale in a numbered or labeled section. Each section pairs a UHC criterion with patient-specific evidence that satisfies it. Closes with a specific request for action and a contact path. |
| 9-10 | All of 7-8 plus pre-empts likely UHC counter-arguments (e.g., "if the reviewer believes a preferred biosimilar trial is required, the patient's documented infusion reaction to bevacizumab-bvzr on [date] satisfies the policy's intolerance exception"). Uses structure consistent with UHC's own clinical-criteria decision tree. |

---

## Axis 5 — Likelihood of Overturn (1-10)

**What it measures:** The judge LLM's holistic probability estimate that an independent external reviewer (or a UHC peer-to-peer oncologist) would overturn the denial.

| Score | Anchor |
|---|---|
| 1-3 | The denial reasons are likely correct or under-addressed. Overturn unlikely. |
| 4-6 | Even-odds case. Some criteria are met, others are weakly addressed. A skilled reviewer might overturn but it is not the most-likely outcome. |
| 7-8 | The appeal satisfies the explicit UHC policy criteria. An external reviewer applying NCCN compendium logic would likely overturn. AMA / KFF data show ~80% of oncology denials are overturned on appeal when NCCN evidence is presented; this appeal meets that bar. |
| 9-10 | The appeal is grounded in a Category 1 NCCN recommendation directly applicable to the patient, cites FDA-approved labeling, and addresses every denial criterion with specific evidence. Overturn is highly likely on first-level review without need for external escalation. |

---

## Composite scoring

```
composite = mean(axis_1, axis_2, axis_3, axis_4, axis_5)
```

- Gold dataset eligibility: `composite ≥ 7` AND `axis_2 (Policy Citation Quality) ≥ 7` AND no negative-selection failure.
- Tournament winner: highest composite from median-of-3 judge runs (per `granum/center/judge.py`).
- Tombstone trigger: composite < 5 OR `axis_2 < 4` (hallucinated or absent citations).

---

## English-feedback requirement

The judge MUST also produce a one-paragraph English critique alongside the scalar scores. Per the Arize / Phoenix "prompt learning over scalars" thesis, the critique is what the next-generation mutator reads to construct improvement mutations. A score of 8 with critique "The biomarker section is precise but the biosimilar step-therapy section omits the documented bevacizumab-bvzr intolerance from 2024-11-12" is more useful than a 7 with critique "OK appeal."
