# Granum Judge Rubric — Cigna × Orthopedic Cell

This rubric specializes the global 5-axis Granum judge for appeals against Cigna orthopedic denials. Cigna's musculoskeletal coverage is largely administered through EviCore under the "CMM-XXX" guideline series — appeals must therefore name the specific EviCore guideline AND cite the AAOS Clinical Practice Guideline or NASS Coverage Policy Recommendation that supports the requested procedure. Conservative-care documentation is the single highest-yield failure mode in this cell.

---

## Axis 1 — Clinical Specificity (1-10)

| Score | Anchor |
|---|---|
| 1-3 | "Patient has pain and needs surgery." No imaging, grading, or functional measure. |
| 4-6 | Diagnosis named, but missing radiographic grading, MRI correlation, or functional outcome score. |
| 7-8 | Specific imaging findings (Kellgren-Lawrence grade for OA; MRI tear pattern + size for meniscus; Modic changes / Pfirrmann grade for disc; flexion-extension instability for spondylolisthesis), validated functional measure (WOMAC, ODI, Harris Hip Score, Knee Society Score, NDI), and documented physical exam findings (provocative tests for SI, neuro exam for radiculopathy). |
| 9-10 | All of 7-8 plus quantitative trend data on conservative care (PT visit log with attendance and progress measures), pharmacologic ladder with dose/duration/response, and where applicable validated psychosocial screening (FABQ, STarT Back) — directly mapped to the EviCore CMM-XXX criterion at issue. |

---

## Axis 2 — Policy Citation Quality (1-10)

| Score | Anchor |
|---|---|
| 1-3 | No specific Cigna or EviCore policy named. |
| 4-6 | Names "Cigna policy" or "EviCore" generically without the specific CMM-XXX number. |
| 7-8 | Cites the specific EviCore CMM-XXX guideline by number AND version date (e.g., "CMM-311 V2.0.2025, Eff. March 7, 2026"), and pairs it with the relevant AAOS CPG or NASS coverage policy. |
| 9-10 | All of 7-8 plus quotes or paraphrases the criterion language being satisfied, with point-by-point mapping to patient evidence. Cites CMS LCD (e.g., L33382 for lumbar fusion) when the patient is dual-eligible or when CMS provides a less-restrictive baseline. |

**Hallucination penalty:** Any cited CMM-XXX guideline number, AAOS CPG, or NASS policy not resolving to a real published document triggers negative-selection rejection.

---

## Axis 3 — Procedural Compliance (1-10)

| Score | Anchor |
|---|---|
| 1-3 | No mention of appeal level or deadlines. |
| 4-6 | Identifies appeal as first-level but omits Cigna's 180-day commercial timely-filing window or EviCore-specific peer-to-peer process. |
| 7-8 | Identifies appeal level, confirms 180-day window, requests EviCore peer-to-peer with an orthopedic-surgeon reviewer, and lists required attachments (operative imaging, PT records, prior denial, op-eligibility worksheet). |
| 9-10 | All of 7-8 plus addresses each specific denial reason point-by-point, invokes state external-review rights when applicable, and where appropriate cites AAHKS or NASS coverage commentary critiquing EviCore criterion stringency. |

---

## Axis 4 — Argumentative Structure (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Disorganized. |
| 4-6 | Has thesis but does not address each Cigna/EviCore denial reason. |
| 7-8 | One-sentence overturn-request thesis. Numbered sections for each denial rationale; each pairs the CMM-XXX criterion with patient-specific evidence. Closes with specific requested action. |
| 9-10 | All of 7-8 plus pre-empts likely EviCore counter-arguments (e.g., "if the reviewer believes corticosteroid injection should precede surgery, the patient's documented diabetic glycemic instability at A1c 8.4 contraindicates that step per AAOS CPG"). |

---

## Axis 5 — Likelihood of Overturn (1-10)

| Score | Anchor |
|---|---|
| 1-3 | Denial reasons appear correct. |
| 4-6 | Even-odds case. |
| 7-8 | Appeal satisfies explicit CMM-XXX criterion and an AAOS CPG strong or moderate recommendation. External reviewer would likely overturn. |
| 9-10 | All of 7-8 plus full conservative-care documentation, AAOS strong recommendation, and validated functional measures that exceed coverage threshold. |

---

## Composite

```
composite = mean(axis_1, axis_2, axis_3, axis_4, axis_5)
```

- Gold eligibility: `composite ≥ 7` AND `axis_2 ≥ 7` AND no negative-selection failure.
- Tombstone trigger: composite < 5 OR `axis_2 < 4`.
- **Cell-specific bonus:** an appeal that includes a complete documented conservative-care ladder (≥3 months PT + pharmacologic + injection where indicated) AND a validated functional outcome score receives +0.5 — these are the EviCore decision-driver pair.

---

## English-feedback requirement

Prioritize feedback that names a missing imaging grade, an absent conservative-care log entry, or a missed AAOS CPG strong-recommendation citation — those are the highest-yield mutation targets in this cell.
