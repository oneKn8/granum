"""Synthetic denial generator for Aetna cardiac demo cell.

Patterns derived from publicly published Aetna Clinical Policy Bulletins
and AMA prior-authorization survey samples. All data synthetic, clearly
labeled — no PHI.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from enum import StrEnum


class DenialReason(StrEnum):
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    LACKS_PRIOR_AUTH = "lacks_prior_auth"
    EXPERIMENTAL_TREATMENT = "experimental_treatment"
    INSUFFICIENT_CLINICAL_DOCUMENTATION = "insufficient_clinical_documentation"
    STEP_THERAPY_REQUIRED = "step_therapy_required"
    DUPLICATE_THERAPY = "duplicate_therapy"
    OUT_OF_NETWORK = "out_of_network"


@dataclass(frozen=True)
class Denial:
    denial_id: str
    payer: str
    diagnosis: str
    cpt_code: str
    icd10_code: str
    patient_age_range: str
    denial_reason: DenialReason
    denial_text: str
    submission_date: str
    appeal_deadline_days: int = 30


# Aetna cardiac denial pattern bank — 10 patterns mapping to real Aetna CPBs.
# Each pattern cites a real Aetna Clinical Policy Bulletin number and a real
# CPT + ICD-10 code. The denial_text is synthetic but structurally accurate.
_AETNA_CARDIAC_PATTERNS: list[dict] = [
    {
        "cpb": "0119",
        "cpt": "93306",
        "icd10": "I25.10",
        "reason": DenialReason.NOT_MEDICALLY_NECESSARY,
        "text": (
            "Coverage denied for echocardiogram (CPT 93306) for patient with stable angina "
            "(ICD-10 I25.10). Aetna Clinical Policy Bulletin 0119 requires documentation of "
            "new or worsening symptoms, abnormal stress test results, or post-procedural "
            "evaluation. Submitted records show stable symptoms over 12-month period without "
            "intervention. Appeal must include specific clinical change justifying repeat imaging. "
            "Appeal deadline: 30 days from this notice."
        ),
    },
    {
        "cpb": "0286",
        "cpt": "33533",
        "icd10": "I25.110",
        "reason": DenialReason.STEP_THERAPY_REQUIRED,
        "text": (
            "Coverage denied for coronary artery bypass grafting (CPT 33533) for patient with "
            "atherosclerotic heart disease with unstable angina (ICD-10 I25.110). Aetna CPB 0286 "
            "requires documented failure of maximally tolerated medical therapy and recent stress "
            "imaging consistent with high-risk anatomy. Submitted records do not include stress "
            "imaging within prior 90 days. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0353",
        "cpt": "93458",
        "icd10": "I20.9",
        "reason": DenialReason.INSUFFICIENT_CLINICAL_DOCUMENTATION,
        "text": (
            "Coverage denied for diagnostic cardiac catheterization (CPT 93458) for patient with "
            "unspecified angina (ICD-10 I20.9). Aetna CPB 0353 requires either positive non-invasive "
            "stress test, intermediate-to-high pretest probability of CAD per ACC/AHA criteria, or "
            "specific high-risk clinical features documented. Submitted notes lack pretest "
            "probability calculation or recent stress imaging. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0535",
        "cpt": "92928",
        "icd10": "I25.110",
        "reason": DenialReason.NOT_MEDICALLY_NECESSARY,
        "text": (
            "Coverage denied for percutaneous coronary intervention with stent placement (CPT 92928) "
            "for patient with unstable angina (ICD-10 I25.110). Aetna CPB 0535 requires evidence of "
            "lesion stenosis >=70% on diagnostic angiography or fractional flow reserve <0.80. "
            "Submitted imaging shows 60% stenosis without functional assessment. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0119",
        "cpt": "93350",
        "icd10": "I50.32",
        "reason": DenialReason.LACKS_PRIOR_AUTH,
        "text": (
            "Coverage denied for stress echocardiogram (CPT 93350) for patient with chronic diastolic "
            "heart failure (ICD-10 I50.32). Aetna CPB 0119 requires prior authorization for stress "
            "imaging studies. No prior authorization submitted before service rendered. Member may "
            "appeal with retrospective documentation of clinical urgency. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0286",
        "cpt": "33361",
        "icd10": "I35.0",
        "reason": DenialReason.EXPERIMENTAL_TREATMENT,
        "text": (
            "Coverage denied for transcatheter aortic valve replacement (CPT 33361) for patient with "
            "nonrheumatic aortic valve stenosis (ICD-10 I35.0). Aetna CPB 0286 covers TAVR only for "
            "patients deemed high-risk or inoperable for surgical aortic valve replacement per "
            "multidisciplinary heart team evaluation. Submitted records lack heart team consult "
            "documentation. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0353",
        "cpt": "93656",
        "icd10": "I48.0",
        "reason": DenialReason.STEP_THERAPY_REQUIRED,
        "text": (
            "Coverage denied for atrial fibrillation ablation (CPT 93656) for patient with paroxysmal "
            "atrial fibrillation (ICD-10 I48.0). Aetna CPB 0353 requires documented failure of at "
            "least one antiarrhythmic medication trial before catheter ablation. Submitted records "
            "show no prior antiarrhythmic therapy. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0535",
        "cpt": "33207",
        "icd10": "I44.2",
        "reason": DenialReason.INSUFFICIENT_CLINICAL_DOCUMENTATION,
        "text": (
            "Coverage denied for permanent pacemaker insertion (CPT 33207) for patient with complete "
            "atrioventricular block (ICD-10 I44.2). Aetna CPB 0535 requires documentation per ACC/AHA "
            "Class I indications including symptoms (syncope, presyncope, fatigue) or specific ECG "
            "findings (sustained pauses >=3 seconds, escape rhythm <40 bpm). Submitted records lack "
            "this documentation. Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0119",
        "cpt": "93303",
        "icd10": "Q23.4",
        "reason": DenialReason.DUPLICATE_THERAPY,
        "text": (
            "Coverage denied for transthoracic echocardiogram (CPT 93303) for patient with congenital "
            "mitral stenosis (ICD-10 Q23.4). Aetna CPB 0119 indicates this study was performed within "
            "the prior 90 days at a contracted facility. Re-imaging requires documented clinical change. "
            "Appeal deadline: 30 days."
        ),
    },
    {
        "cpb": "0286",
        "cpt": "33405",
        "icd10": "I06.0",
        "reason": DenialReason.NOT_MEDICALLY_NECESSARY,
        "text": (
            "Coverage denied for aortic valve replacement, open (CPT 33405) for patient with rheumatic "
            "aortic stenosis (ICD-10 I06.0). Aetna CPB 0286 requires moderate-to-severe symptomatic "
            "aortic stenosis with documented LVEF decline, symptoms (CHF, syncope, angina), or aortic "
            "valve area <1.0 cm^2. Submitted records show mild stenosis (AVA 1.4 cm^2) without symptoms. "
            "Appeal deadline: 30 days."
        ),
    },
]


def generate_denial(*, payer: str, diagnosis: str, seed: int | None = None) -> Denial:
    """Generate a synthetic Aetna cardiac denial.

    Args:
        payer: Must be 'aetna' in v0.1 (other cells added in Phase 2).
        diagnosis: Must be 'cardiac' in v0.1.
        seed: Optional deterministic seed; None for random.

    Returns:
        A Denial dataclass instance with a stable denial_id.

    Raises:
        NotImplementedError if (payer, diagnosis) not in the curated bank.
    """
    if payer != "aetna" or diagnosis != "cardiac":
        raise NotImplementedError(
            f"Pattern bank for ({payer}, {diagnosis}) not yet curated. "
            f"v0.1 supports only ('aetna', 'cardiac')."
        )
    rng = random.Random(seed)
    pattern = rng.choice(_AETNA_CARDIAC_PATTERNS)
    age_low = rng.choice([45, 50, 55, 60, 65, 70])
    age_range = f"{age_low}-{age_low + 5}"
    submission_date = f"2026-{rng.randint(1, 5):02d}-{rng.randint(1, 28):02d}"
    raw_id_seed = (
        f"{pattern['cpt']}-{pattern['icd10']}-{submission_date}-{age_range}-{seed}"
    )
    denial_id = "aetna_cardiac_" + hashlib.sha1(raw_id_seed.encode()).hexdigest()[:12]
    return Denial(
        denial_id=denial_id,
        payer=payer,
        diagnosis=diagnosis,
        cpt_code=pattern["cpt"],
        icd10_code=pattern["icd10"],
        patient_age_range=age_range,
        denial_reason=pattern["reason"],
        denial_text=pattern["text"],
        submission_date=submission_date,
    )
