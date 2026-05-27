# Cell Curation Methodology — How the (Payer × Diagnosis) Data Was Built

Granum demonstrates a self-improving appeal-writing agent across five (payer × diagnosis) cells: Aetna × cardiac (the reference cell, owned by Terminal A), UnitedHealthcare × oncology, Anthem (Elevance) × mental health, Cigna × orthopedic, and Humana × endocrinology (the four new cells, this document). This document describes how each new cell was sourced so that a judge spot-checking the data can verify legitimacy.

## What "synthetic but grounded" means here

Every denial pattern, citation, and gold appeal in this repository is **synthetic data** — fictional patient scenarios constructed for demonstration. None of it reflects real patient encounters, real Protected Health Information, or real adjudicated claim outcomes. The synthesis is grounded, however, in publicly published material that any reviewer can independently verify:

- **CPT and HCPCS codes** are real codes from the AMA CPT and CMS HCPCS code sets.
- **ICD-10-CM codes** are real codes from the official ICD-10-CM coding system.
- **Drug names** (brand and generic) and FDA-approved indications are real and match current FDA labeling at the time of curation (2026-05-27).
- **Payer policy titles** are real titles from the public-provider-portal-published policies of each payer; URLs in `valid_citations.json` resolve to live pages (verify on the curation date).
- **Clinical guideline citations** (NCCN, AAOS, ASTRO, NASS, ADA, AACE, APA, ASAM, LOCUS, CALOCUS-CASII) reference real guidelines from real organizations with real publication URLs.
- **Patient demographic details, dates, and clinical narratives** are fictional.

This approach mirrors the Aetna cardiac reference cell created by Terminal A in `data/aetna_cardiac/` and matches the data disclaimer pattern already established in `src/granum/data/denials.py` ("Patterns derived from publicly published CMS denial taxonomies and AMA prior-authorization survey samples. All data synthetic and clearly labeled.").

## Per-cell sourcing

### UnitedHealthcare × Oncology

Primary policy sources:

- UnitedHealthcare Commercial Medical Drug Policy: *Oncology Medication Clinical Coverage* (effective April 1, 2026), published on the UHC provider portal. This policy is the master document governing prior authorization for injectable oncology medications under the medical benefit, and it explicitly references the NCCN Drugs & Biologics Compendium as the basis for coverage.
- UnitedHealthcare Oxford Clinical Policy: *Proton Beam Radiation Therapy* — used to ground the chordoma and adult-glioma denial patterns.
- UnitedHealthcare Commercial Medical Drug Policies on *Intensity-Modulated Radiation Therapy* and *Stereotactic Body Radiation Therapy and Stereotactic Radiosurgery*.
- UnitedHealthcare Clinical Policy: *Chimeric Antigen Receptor T-Cell (CAR T) Therapy*.
- Optum CGP integration for outpatient chemotherapy (effective June 1, 2026 per UHC May 2026 Monthly Overview).

Guideline anchors:

- NCCN Clinical Practice Guidelines in Oncology, Versions 1-5 of 2026 across cancer types (Breast V.1.2026 Jan 16 2026; Non-Small Cell Lung Cancer V.5.2026; Colon; Pancreatic; Melanoma; B-Cell Lymphomas; Multiple Myeloma; Acute Myeloid Leukemia; etc.).
- NCCN Drugs & Biologics Compendium (used by UHC as the basis for off-label oncology medication coverage).
- ASTRO Model Policies on Proton Beam Therapy and Stereotactic Body Radiation Therapy.
- FDA-approved prescribing information for Keytruda, Yescarta, Enhertu, Lynparza, Mounjaro/Ozempic etc.

Denial patterns chosen to span the seven `DenialReason` enum values in `src/granum/data/denials.py` (not_medically_necessary, lacks_prior_auth, experimental_treatment, insufficient_clinical_documentation, step_therapy_required, duplicate_therapy, out_of_network) and to cover diverse oncology modalities: cytotoxic chemotherapy, targeted therapy, immunotherapy, radiation oncology (IMRT, SBRT, proton), CAR-T cell therapy, biosimilar step therapy, comprehensive genomic profiling.

### Anthem (Elevance) × Mental Health

Primary policy sources:

- Anthem Clinical UM Guidelines, CG-BEH series, accessed via the Anthem provider portal (https://www.anthem.com/provider/policies/clinical-guidelines/). Specific guidelines cited include CG-ADMIN-01 (Pre-Payment Review Medical Necessity Determinations), CG-BEH-02 (Adaptive Behavior Treatment), and CG-BEH-14 (Intensive In-home Behavioral Health Services).
- Anthem's licensed *MCG Behavioral Health Care Guidelines (BHG)* — explicitly named in Anthem CUMG documentation as the primary inpatient/PHP/IOP/residential criteria framework.
- Anthem Behavioral Health Reference Guide and provider-portal policy compilations (e.g., CA CAID, OH CAID, IN CAID compilations dated 2024 and 2025).
- Anthem Express Medical Policy and Clinical UM Guideline Updates (January 2026) for current effective-date references.

Adopted external tools (per Anthem documentation when MCG BHG is silent):

- **LOCUS** (Level of Care Utilization System) for adults — American Association for Community Psychiatry.
- **CALOCUS-CASII** for children/adolescents (ages 6-18) — joint AACAP/AACP unified instrument.
- **ECSII** for early childhood.
- **ASAM Criteria, Fourth Edition (2023)** for substance use disorder level of care.

Guideline anchors:

- APA Practice Guidelines (Major Depressive Disorder 2019; Bipolar Disorder; Schizophrenia; PTSD/Acute Stress; Antipsychotics; Alcohol Use Disorder pharmacological treatment).
- AACAP Practice Parameters for pediatric and adolescent conditions.
- SAMHSA TIP 63 for medications for opioid use disorder.

Parity-law overlay:

- **MHPAEA** (Mental Health Parity and Addiction Equity Act).
- **Wit v. UBH** (Northern District of California 2019, partially reversed by the Ninth Circuit 2022; remains a touchstone for NQTL parity analysis).
- ARC Issue Brief: Key Parity Definitions and Medical Necessity Criteria (March 2025).
- Anthem Mental Health Parity Settlement reporting (Behavioral Health Business, January 2026).

Denial patterns chosen to span inpatient psychiatric admission, IOP, PHP, rTMS, ECT, residential SUD, withdrawal management, adaptive behavior treatment (ABA), concurrent outpatient psychotherapy, diagnostic evaluation, and continued-stay review.

### Cigna × Orthopedic

Primary policy sources:

- Cigna's musculoskeletal coverage is largely administered through **EviCore** under the CMM-XXX guideline series. Specific guidelines cited include:
  - **CMM-311** Knee Replacement Arthroplasty (V2.0.2025, effective March 7, 2026).
  - **CMM-312** Knee Surgery — Arthroscopic and Open Procedures (effective March 7, 2026).
  - **CMM-609** Lumbar Fusion (Arthrodesis) (V2.0.2025, effective December 18, 2025).
  - **CMM-606** Cervical Spine Surgery.
- Cigna Medical Coverage Policy **0303** Lumbar Fusion for Spinal Instability and Degenerative Disc Conditions.
- Cigna Medical Coverage Policy **0515** Musculoskeletal Procedures.
- Cigna Medical Coverage Policy **0347** Minimally Invasive Knee Replacement.
- EviCore Musculoskeletal Services-Procedures Guideline Set.

Guideline anchors:

- AAOS Clinical Practice Guideline: *Management of Osteoarthritis of the Knee (Non-Arthroplasty)*, 3rd Edition (2021).
- AAOS Appropriate Use Criteria: *Management of Osteoarthritis of the Knee (Non-Arthroplasty)* (2022).
- AAOS Clinical Practice Guideline: *Management of Osteoarthritis of the Hip* (2024).
- AAHKS (American Association of Hip and Knee Surgeons) position statements.
- NASS (North American Spine Society) Coverage Policy Recommendations on Lumbar Fusion (2021) and Lumbar Discectomy.
- APTA (American Physical Therapy Association) CPG on Hip Osteoarthritis Management.

Validated outcome measures referenced in denials and appeals:

- WOMAC, Knee Society Score, Harris Hip Score, Oswestry Disability Index, Fear-Avoidance Beliefs Questionnaire.

CMS overlays:

- CMS Local Coverage Determination L33382 (Lumbar Spinal Fusion).
- CMS Medicare Coverage Database Article A52369 (Arthroscopic Lavage and Debridement for OA Knee).

Denial patterns span TKA, knee arthroscopy/meniscectomy, single-level and combined lumbar fusion, lumbar discectomy, THA, autologous chondrocyte implantation, diagnostic arthroscopy, SI joint fusion, revision TKA for prosthetic joint infection, cervical fusion for myelopathy, and minimally invasive unicompartmental arthroplasty.

### Humana × Endocrinology

Primary policy sources:

- Humana Medical and Pharmacy Coverage Policies (MCP) portal at https://mcp.humana.com/tad/tad_new/home.aspx (the canonical Humana policy-search interface used by providers).
- Specific MCPs referenced: GLP-1 Receptor Agonists for Type 2 Diabetes; Anti-Obesity GLP-1 Receptor Agonists; External Insulin Infusion Pumps; Continuous Glucose Monitors; Insulin Pumps; PCSK9 Inhibitors; SGLT-2 Inhibitors.
- Humana Group Medicare Advantage Continuous Glucose Monitor Member Flyer (2026).
- Humana Dexcom Provider Flyer (2026).
- Humana Diabetic Supply Policy Provider Letter (effective January 1, 2025) — establishes the unified-DME-or-pharmacy channel requirement.
- Humana Military / TRICARE Medical Policy MP23-034E (2024) for CGM in the military population.
- Humana CGM trend press release (2026).
- Humana Exception and Appeals Process Information and Medical Organization Determination pages.

Guideline anchors:

- ADA *Standards of Care in Diabetes—2026* (Diabetes Care Vol. 49 Suppl. 1, with documented elevations for GIP/GLP-1 RA therapy in patients with concurrent obesity, MASLD/MASH, HFpEF, CKD, and established ASCVD — Figure 9.4).
- AACE Clinical Practice Guidelines (Comprehensive Type 2 Diabetes Management Algorithm; Obesity Management Algorithm; Use of Continuous Glucose Monitoring).
- Endocrine Society Clinical Practice Guidelines on Obesity Pharmacotherapy and Diabetes Technology.
- FDA-approved prescribing information for Ozempic, Wegovy, Mounjaro, Zepbound, Trulicity, Rybelsus, Repatha.

Federal regulatory overlay:

- CMS National Coverage Determination 280.14 (Continuous Glucose Monitoring).
- CMS-0057-F Interoperability and Prior Authorization Final Rule (effective January 1, 2026; mandates 7-day standard / 72-hour expedited MA decision timelines with auto-escalation to the Maximus IRE on missed deadlines).
- Inflation Reduction Act insulin-cost cap provision.

Denial patterns span GLP-1 step-therapy denials (Ozempic / Wegovy / Mounjaro / Zepbound / Trulicity / Rybelsus / dapagliflozin / evolocumab), insulin pump initiation and AID upgrade, CGM sensor and transmitter access including the unified-channel sourcing rule, and the Part D obesity-indication structural exclusion vs. the OSA-indication carve-out for Zepbound following the December 2024 FDA approval.

## How to spot-check the data

1. Open any `data/<cell>/valid_citations.json`. Click any URL — it should resolve to a real published page on the payer's provider portal, the guideline organization's website, or the FDA's drugs@FDA database.
2. Open any `data/<cell>/denial_templates.json`. Every CPT, HCPCS, and ICD-10 code is a real code searchable at https://www.aapc.com/codes/ or https://www.cms.gov/medicare/coding-billing/icd-10-codes.
3. Open any `data/<cell>/gold_appeals.jsonl`. Every citation in the `citations` field of every line is a member of the same cell's `valid_citations.json` — this is enforced by `src/granum/center/negative_selection.py` at training and tournament time.
4. Cross-reference any specific clinical-criterion claim in a denial template against the named policy. For example, "PD-L1 TPS ≥50% for first-line single-agent pembrolizumab in NSCLC" is verifiable in NCCN NSCLC V.5.2026 and the FDA-approved Keytruda labeling.

## Limitations

- **No real outcomes.** The `outcome: overturned` and `judge_score` fields in `gold_appeals.jsonl` are curator-assigned, not adjudicated by a real payer. They represent expert-curated exemplars of what high-quality appeals look like, used as anchors for the LLM-as-judge tournament. The tournament's value is measured by whether judge-score correlates with the appeal's adherence to the cell-specific rubric, not by external real-world overturn rates.
- **Policies change.** Payer policies are updated quarterly to annually. The curation date (2026-05-27) is recorded in each `denial_templates.json` `_meta` block. Antigen drift is the mechanism Granum uses to handle this in production; for the hackathon demo, the policies as cited at curation are sufficient.
- **No PHI.** All patient-specific details are fictional. Any resemblance to real patients is coincidental.

## Why this matters for the hackathon

The Arize Phoenix track judges will look at whether the demo system implements a real self-improvement loop with real data. Hallucinated CPB numbers or fictional NCCN sections would be the fastest way to fail credibility on spot check. The negative-selection gate in `src/granum/center/negative_selection.py` is the agent's structural answer to that risk: it cannot pass an unverified citation through to the tournament. This document is the human-side answer: every citation a curator added is traceable, every code is real, and the data substrate the agent evolves on is grounded in publicly verifiable medical-policy and clinical-guideline material.
