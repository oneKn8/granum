# Granum Judge Rubric — UnitedHealthcare × Oncology Cell

Score a candidate appeal letter on 5 axes, each 1-10. Composite = mean of the axes.
Be EXACTING and DISCRIMINATING: a generic "this treatment is medically necessary"
appeal with no policy grounding scores 3-5. Reserve 8-10 for appeals that fully meet
the anchor. Score the candidate RELATIVE to the gold reference appeals provided — those
are 9-quality; an appeal visibly less grounded or less structured scores lower.

**Score on what a good appeal can do with the FACTS IN THE DENIAL.** The appeal must
NOT fabricate clinical data. Do NOT require lab values, biomarker percentages, or
staging the denial did not supply. Reward correct USE of the facts that ARE available
— the diagnosis (ICD-10), the requested agent and its therapeutic target/indication,
the denial reason, and the controlling policy — plus sound, policy-grounded argument.
An appeal is never penalized for omitting a number it was never given; it IS penalized
for failing to connect the requested drug to the patient's cancer and to the policy.

---

## Axis 1 — Clinical Specificity (1-10)

How concretely the appeal grounds the patient's clinical picture in the facts available
and ties them to UHC's medical-necessity standard.

- **9-10**: Names the diagnosis (ICD-10) and the requested agent's therapeutic target /
  on-label indication (e.g., HER2-directed therapy for HER2-positive breast cancer),
  states the line of therapy and the prior-therapy or intolerance context the denial
  implies, and ties each clinical fact to the specific coverage criterion it satisfies.
- **6-8**: Diagnosis plus the agent-to-target relationship is stated, and at least one
  coverage criterion is linked to a patient fact.
- **3-5**: General clinical language ("the patient needs this drug", "medically
  necessary") with no diagnosis-to-agent rationale. **Cap here if the appeal does not
  connect the requested agent to the patient's specific cancer.**
- **1-2**: No clinical specifics at all.

---

## Axis 2 — Policy Citation Quality (1-10)

Accuracy and specificity of UnitedHealthcare and NCCN citations.

- **9-10**: Names the controlling UHC oncology policy AND the applicable NCCN guideline
  or category (or the NCCN Drugs & Biologics Compendium for off-label use), and maps the
  criterion language to the patient's facts. FDA labeling cited when the use is on-label.
- **6-8**: Names the correct UHC policy AND an NCCN reference, but without mapping the
  criterion to patient facts.
- **3-5**: Names a UHC policy with no NCCN/guideline support, or only "the policy
  states". **Cap here if there is no NCCN reference.**
- **1-2**: No UHC policy reference.

Hallucinated citations are rejected at negative selection BEFORE scoring; any citation
that reaches the judge resolves to real published UHC or NCCN material.

---

## Axis 3 — Procedural Compliance (1-10)

Adherence to UnitedHealthcare appeal procedural rules.

- **9-10**: Names the appeal level (first-level internal, expedited, or external
  review), confirms submission within the 65-day commercial timely-filing window,
  addresses each denial reason point-by-point, and requests peer-to-peer review with a
  board-certified oncologist.
- **6-8**: Appeal level plus timely-filing acknowledgment, missing 1-2 of the above.
- **3-5**: Mentions a deadline or reconsideration but omits the appeal level. **Cap here
  if there is no timely-filing reference.**
- **1-2**: No procedural language.

---

## Axis 4 — Argumentative Structure (1-10)

Logical flow and persuasive construction.

- **9-10**: Opens with a one-sentence overturn-request thesis. Addresses each denial
  rationale in its own labeled section pairing a policy criterion with patient evidence.
  Pre-empts the likely UHC counter-argument. Closes with a specific action request and a
  contact path.
- **6-8**: Clear thesis and sections, with one logical gap.
- **3-5**: An argument exists but it is disorganized or merely asserts conclusions.
- **1-2**: A list of grievances, no argument.

---

## Axis 5 — Likelihood of Overturn (1-10)

Holistic: would an external reviewer applying NCCN logic, or a UHC peer-to-peer
oncologist, overturn the denial on this appeal alone?

- **9-10**: Grounded in an applicable NCCN recommendation and the controlling UHC
  criterion, with every denial reason answered. Overturn highly likely on first-level
  review.
- **6-8**: Satisfies the explicit policy criteria; probable overturn.
- **3-5**: Even-odds; a key criterion is weakly addressed. **Default here for any appeal
  lacking BOTH an NCCN reference AND criterion-to-fact mapping.**
- **1-2**: Denial reasons under-addressed; overturn unlikely.

---

## Output

Return ONLY JSON with keys: `clinical_specificity`, `policy_citation_quality`,
`procedural_compliance`, `argumentative_structure`, `likelihood_overturn`,
`english_feedback`.

## English-feedback requirement

The judge MUST also produce a one-paragraph English critique (200-400 characters). Name
the SPECIFIC weakest axis and the single highest-leverage fix — concrete enough that a
rewrite can act on it directly. Examples: "names the UHC policy but cites no NCCN
category — add the applicable NCCN guideline and its category", or "no criterion-to-fact
mapping — tie the HER2-positive status to the policy's coverage criterion it satisfies".
Per the prompt-learning-over-scalars thesis, this critique is what the next-generation
mutator reads to construct its improvement.
