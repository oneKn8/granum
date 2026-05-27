# Granum Judge Rubric — Humana × Endocrinology Cell

This rubric specializes the global 5-axis Granum judge for Humana endocrinology denials. Humana's endocrinology footprint is heavily Medicare Advantage and Medicare Part D, which means tighter appeal-deadline math (65 days for MA), explicit CMS NCD overlay (especially NCD 280.14 for CGM), and a Part D structural limitation on obesity-indication GLP-1 coverage that frequently drives denials. The cell weights step-therapy completeness, CMS-NCD compliance, and FDA-indication alignment.

---

## Axis 1 — Clinical Specificity (1-10)

| Score | Anchor |
|---|---|
| 1-3 | "Patient has diabetes and needs medication." No A1C, no medication history. |
| 4-6 | Diagnosis named, but missing A1C within 90 days, complete prior-medication ladder, or required device-supporting data. |
| 7-8 | Most recent A1C with date, complete prior-medication ladder (drug, dose, duration, response, reason for discontinuation), BMI trend, comorbidity list (ASCVD, HF, CKD, MASH), CGM data (Time-in-Range, Time-Below-Range) for diabetes-tech requests, C-peptide assay where relevant. |
| 9-10 | All of 7-8 plus quantitative trend data (A1C trajectory, weight trajectory, hypoglycemia event log, CGM Ambulatory Glucose Profile metrics), explicit linkage of each fact to the Humana MCP criterion at issue, and FDA-labeled indication mapped to the patient's specific clinical phenotype. |

---

## Axis 2 — Policy Citation Quality (1-10)

| Score | Anchor |
|---|---|
| 1-3 | No specific Humana policy named. |
| 4-6 | References "Humana coverage policy" generically without the specific MCP policy. |
| 7-8 | Cites the specific Humana MCP policy by title (e.g., "Humana MCP: GLP-1 Receptor Agonists for Type 2 Diabetes"), pairs with the ADA Standards of Care—2026 section, and where relevant cites the FDA-approved prescribing information. |
| 9-10 | All of 7-8 plus invokes CMS NCD 280.14 (CGM) or CMS-0057-F as appropriate, addresses Part D coverage structure when at issue (e.g., obesity-indication exclusion for GLP-1 absent established CVD), and quotes the specific MCP criterion paragraph being satisfied. |

**Hallucination penalty:** Any cited Humana MCP policy or guideline not resolving to a real published document triggers negative-selection rejection.

---

## Axis 3 — Procedural Compliance (1-10)

| Score | Anchor |
|---|---|
| 1-3 | No appeal-level or deadline reference. |
| 4-6 | Identifies appeal level but mis-applies the 65-day MA timely-filing window (vs 180 days commercial). |
| 7-8 | Identifies appeal level, confirms submission within the correct window (65 days for Medicare Advantage; 180 days for commercial), names the correct submission channel (Resolutions.Humana.com, P.O. Box 14546 Lexington KY 40512-4546). Requests peer-to-peer review with an endocrinologist (or endocrinologist-supervised pharmacist for GLP-1 cases). |
| 9-10 | All of 7-8 plus addresses each denial reason point-by-point, invokes CMS-0057-F decision-timeline guarantees (7-day standard / 72-hour expedited), and where applicable notes auto-escalation to the IRE (Maximus) for missed Humana deadlines. |

---

## Axis 4 — Argumentative Structure (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Disorganized. |
| 4-6 | Has thesis but does not address each specific Humana criterion. |
| 7-8 | One-sentence overturn-request thesis. Numbered sections for each denial rationale; each pairs an MCP criterion with patient-specific evidence. Closes with specific requested action. |
| 9-10 | All of 7-8 plus pre-empts likely Humana counter-arguments (e.g., "if the reviewer believes basal-only insulin disqualifies the patient from CGM coverage, note the patient is documented as titrating to a basal-bolus regimen with starting bolus dose on the attached order"). Where applicable, invokes ADA Standards of Care—2026's elevated GLP-1 recommendations for ASCVD/HF/CKD/MASH/obesity. |

---

## Axis 5 — Likelihood of Overturn (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Denial reasons appear correct. |
| 4-6 | Even-odds case. |
| 7-8 | Appeal satisfies the explicit Humana MCP criterion AND ADA Standards-of-Care 2026 supports the requested management. Likely overturn at IRE if not at organization-determination reconsideration. |
| 9-10 | All of 7-8 plus full step-therapy documentation, FDA-labeled indication match, and CMS NCD compliance — overturn highly likely at first-level reconsideration without IRE escalation. |

---

## Composite

```
composite = mean(axis_1, axis_2, axis_3, axis_4, axis_5)
```

- Gold eligibility: `composite ≥ 7` AND `axis_2 ≥ 7` AND no negative-selection failure.
- Tombstone trigger: composite < 5 OR `axis_2 < 4`.
- **Cell-specific bonus:** an appeal that establishes a complete documented step-therapy ladder AND maps the patient's phenotype to a specific ADA Standards-of-Care 2026 elevated-priority indication (ASCVD, HF, CKD, MASH, obesity-with-CVD) receives +0.5 — the highest-yield combination for Humana Medicare Advantage endocrinology overturn.

---

## English-feedback requirement

Prioritize feedback that names a missing A1C, a step-therapy gap, an absent CGM ambulatory-glucose-profile data point, or a missed ADA-2026 cardiorenal indication argument — those are the highest-yield mutation targets in this cell.
