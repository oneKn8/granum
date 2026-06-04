// Granum web — deterministic mock data
//
// Dev fixture + offline fallback. Shape mirrors the live API payload (lib/types.ts)
// so swapping to the real API is a feature-flag flip, not a refactor. The
// aetna_cardiac lineage below is enriched to mirror the real demo arc: a naive
// gen-0 seed (0.40) maturing to a 0.98 champion across 10 generations, with a
// bushy field of apoptosed dead-ends and one bright survival spine seed→champion.

import type {
  BCellStrategy,
  CellId,
  CellMeta,
  CellPayload,
  CoEvolutionState,
  Denial,
  FitnessPoint,
  TournamentRound,
} from "./types";

const isoDaysAgo = (d: number): string => {
  // Frozen reference date so screenshots are reproducible across demo runs.
  const REF = new Date("2026-05-27T15:00:00Z").getTime();
  return new Date(REF - d * 86_400_000).toISOString();
};

// ---------- aetna_cardiac — the demo hero cell (10 generations, 0.40 → 0.98) ----------
//
// Branching structure (• = on the survival spine seed→champion):
//   g0  •000 seed
//   g1  •001 ───────────────── 002 (narrative dead-end)
//   g2  •003 ───────────────── 004 (peer-to-peer dead-end)
//   g3  •005 ───────────────── 006 (emotional dead-end)
//   g4  •007 ───────────────── 008 (threat dead-end)
//   g5  •009 ───────────────── 010 (reorder dead-end)
//   g6  •011 ───────────────── 012 (appendix dead-end)
//   g7  •013 ──── 014, 015 (two dead-ends)
//   g8  •016 ───────────────── 017 (statutory dead-end)
//   g9  •018 CHAMPION ──── 019 alive, 020 alive

const aetnaStrategies: BCellStrategy[] = [
  {
    id: "bc_ae_000",
    cell: "aetna_cardiac",
    generation: 0,
    parentId: null,
    label: "L0 — naive template",
    promptBody:
      "You are a physician writing a prior-authorization appeal. State the requested service, attach the clinical notes, and assert that the care is medically necessary. Keep it short.",
    mutationNote: null,
    fitness: 0.4,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(70),
    killedAt: isoDaysAgo(63),
    citations: ["ACC/AHA 2023 Chest Pain Guideline"],
  },
  {
    id: "bc_ae_001",
    cell: "aetna_cardiac",
    generation: 1,
    parentId: "bc_ae_000",
    label: "L1.a — invoke Aetna CPB 0228",
    promptBody:
      "Frame the appeal as an Aetna Clinical Policy Bulletin 0228 (Cardiac Imaging) compliance argument. Quote the controlling section. Attach the patient's symptom-onset timeline as a numbered exhibit. Assert medical necessity.",
    mutationNote: "swap citation: generic ACC/AHA → controlling Aetna CPB 0228",
    fitness: 0.55,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(63),
    killedAt: isoDaysAgo(56),
    citations: ["Aetna CPB 0228 §IV.A"],
  },
  {
    id: "bc_ae_002",
    cell: "aetna_cardiac",
    generation: 1,
    parentId: "bc_ae_000",
    label: "L1.b — narrative-first",
    promptBody:
      "Open with a one-paragraph patient narrative emphasizing functional decline. Defer all clinical citations to a closing appendix. Keep the body warm and human.",
    mutationNote: "reframe: lead with patient story, defer the clinical bullets",
    fitness: 0.43,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(63),
    killedAt: isoDaysAgo(61),
    citations: [],
  },
  {
    id: "bc_ae_003",
    cell: "aetna_cardiac",
    generation: 2,
    parentId: "bc_ae_001",
    label: "L2.a — cross-cite ACC/AHA",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Cross-cite the ACC/AHA 2023 Chest Pain Guideline, Recommendation 3.2, alongside the policy. Attach the symptom-onset timeline; use the phrase 'medically necessary' verbatim.",
    mutationNote: "add authority: ACC/AHA 2023 §3.2 cross-reference to the policy cite",
    fitness: 0.63,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(56),
    killedAt: isoDaysAgo(49),
    citations: ["Aetna CPB 0228 §IV.A.3", "ACC/AHA 2023 §3.2"],
  },
  {
    id: "bc_ae_004",
    cell: "aetna_cardiac",
    generation: 2,
    parentId: "bc_ae_001",
    label: "L2.b — peer-to-peer request",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Open with an explicit request for a peer-to-peer review with a cardiology MD reviewer. Cite the policy appendix governing reviewer qualifications.",
    mutationNote: "add procedural ask: peer-to-peer review with a cardiology reviewer",
    fitness: 0.58,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(56),
    killedAt: isoDaysAgo(49),
    citations: ["Aetna CPB 0228 §IV.A.3", "Aetna CPB 0228 Appendix B"],
  },
  {
    id: "bc_ae_005",
    cell: "aetna_cardiac",
    generation: 3,
    parentId: "bc_ae_003",
    label: "L3.a — quantitative symptom table",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance with an ACC/AHA 2023 §3.2 cross-cite. Replace the symptom narrative with a quantitative table: pain frequency, exercise-tolerance-test failure points, and NYHA class progression. Use 'medically necessary' verbatim.",
    mutationNote: "swap exhibit: prose symptom narrative → quantitative clinical table",
    fitness: 0.71,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(49),
    killedAt: isoDaysAgo(42),
    citations: ["Aetna CPB 0228 §IV.A.3", "ACC/AHA 2023 §3.2"],
  },
  {
    id: "bc_ae_006",
    cell: "aetna_cardiac",
    generation: 3,
    parentId: "bc_ae_003",
    label: "L3.b — emotional appeal",
    promptBody:
      "Frame as Aetna CPB 0228 compliance but lead each section with the human cost of delay — missed work, fear, family impact. Keep the clinical table but subordinate it to the patient's lived experience.",
    mutationNote: "tone shift: foreground emotional stakes over the clinical record",
    fitness: 0.49,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(49),
    killedAt: isoDaysAgo(47),
    citations: ["Aetna CPB 0228 §IV.A.3"],
  },
  {
    id: "bc_ae_007",
    cell: "aetna_cardiac",
    generation: 4,
    parentId: "bc_ae_005",
    label: "L4.a — prior overturned precedents",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance with an ACC/AHA 2023 §3.2 cross-cite and a quantitative symptom table. Reference two prior Aetna overturned appeals (de-identified) with a similar diagnostic profile as persuasive precedent.",
    mutationNote: "add evidence: two de-identified prior Aetna cardiac overturns",
    fitness: 0.78,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(42),
    killedAt: isoDaysAgo(35),
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent: 2024 Aetna overturn, dx I25.10",
    ],
  },
  {
    id: "bc_ae_008",
    cell: "aetna_cardiac",
    generation: 4,
    parentId: "bc_ae_005",
    label: "L4.b — external-review threat",
    promptBody:
      "Frame as Aetna CPB 0228 compliance. Close with explicit notice that the denial will be escalated to state external review under the applicable insurance code within five business days if upheld.",
    mutationNote: "add escalation: external-review threat clause in the close",
    fitness: 0.66,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(42),
    killedAt: isoDaysAgo(35),
    citations: ["Aetna CPB 0228 §IV.A.3", "State insurance code (external review)"],
  },
  {
    id: "bc_ae_009",
    cell: "aetna_cardiac",
    generation: 5,
    parentId: "bc_ae_007",
    label: "L5.a — preempt secondary denials",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Preempt Aetna's three most common secondary denial reasons — insufficient symptom duration, missed step-therapy, and lack of specialist referral — with affirmative exhibits A, B, and C. Cite the ACC/AHA cross-reference and two prior overturns.",
    mutationNote: "preempt: affirmative exhibits for the 3 common secondary denials",
    fitness: 0.84,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(35),
    killedAt: isoDaysAgo(28),
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent ×2",
    ],
  },
  {
    id: "bc_ae_010",
    cell: "aetna_cardiac",
    generation: 5,
    parentId: "bc_ae_007",
    label: "L5.b — exhibit reorder",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Reorder the exhibits so the prior overturned precedents lead, ahead of the clinical table, on the theory that precedent anchors the reviewer first.",
    mutationNote: "structural: precedents-first exhibit ordering",
    fitness: 0.79,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(35),
    killedAt: isoDaysAgo(28),
    citations: ["Aetna CPB 0228 §IV.A.3", "Internal precedent ×2"],
  },
  {
    id: "bc_ae_011",
    cell: "aetna_cardiac",
    generation: 6,
    parentId: "bc_ae_009",
    label: "L6.a — 'medically necessary' ×6",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Distribute Aetna's exact 'medically necessary' phrase six times — across the symptom section, every exhibit caption, and the closing paragraph. Keep the affirmative exhibits preempting the three secondary denials.",
    mutationNote: "verbiage: repeat the payer's 'medically necessary' term verbatim ×6",
    fitness: 0.9,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(28),
    killedAt: isoDaysAgo(21),
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent ×2",
    ],
  },
  {
    id: "bc_ae_012",
    cell: "aetna_cardiac",
    generation: 6,
    parentId: "bc_ae_009",
    label: "L6.b — appendix consolidation",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Consolidate all exhibits into a single indexed appendix to shorten the body, on the theory that a leaner letter reads faster.",
    mutationNote: "compression: fold exhibits into one indexed appendix",
    fitness: 0.82,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(28),
    killedAt: isoDaysAgo(21),
    citations: ["Aetna CPB 0228 §IV.A.3", "Internal precedent ×2"],
  },
  {
    id: "bc_ae_013",
    cell: "aetna_cardiac",
    generation: 7,
    parentId: "bc_ae_011",
    label: "L7.a — §IV.A.3.b sub-clause",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance, attributing the controlling language to the specific §IV.A.3.b sub-clause. ACC/AHA 2023 §3.2 cross-cite. 'Medically necessary' verbatim ×6. Affirmative exhibits A, B, C preempting the three secondary denials.",
    mutationNote: "precision: attribute to the exact §IV.A.3.b sub-clause",
    fitness: 0.94,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(21),
    killedAt: isoDaysAgo(14),
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "ACC/AHA 2023 §3.2",
      "Internal precedent ×2",
    ],
  },
  {
    id: "bc_ae_014",
    cell: "aetna_cardiac",
    generation: 7,
    parentId: "bc_ae_011",
    label: "L7.b — cost-of-delay argument",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Add an actuarial cost-of-delay argument: the downstream cost of an adverse cardiac event exceeds the imaging cost. Keep the verbatim phrasing and exhibits.",
    mutationNote: "add argument: actuarial cost-of-delay framing",
    fitness: 0.85,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(21),
    killedAt: isoDaysAgo(15),
    citations: ["Aetna CPB 0228 §IV.A.3", "Internal precedent ×2"],
  },
  {
    id: "bc_ae_015",
    cell: "aetna_cardiac",
    generation: 7,
    parentId: "bc_ae_011",
    label: "L7.c — physician credential block",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Add a signed attending-physician credential block — NPI, state license, board certification — to the close, asserting reviewer-equivalent authority.",
    mutationNote: "add authority: signed physician credential block",
    fitness: 0.88,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(21),
    killedAt: isoDaysAgo(15),
    citations: ["Aetna CPB 0228 §IV.A.3", "Physician NPI + state license"],
  },
  {
    id: "bc_ae_016",
    cell: "aetna_cardiac",
    generation: 8,
    parentId: "bc_ae_013",
    label: "L8.a — reviewer-cognition order",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3.b compliance. Sequence the letter for reviewer cognition: controlling sub-clause first, quantitative table second, precedent third, ACC/AHA cross-cite fourth. 'Medically necessary' verbatim ×6. Affirmative exhibits A, B, C.",
    mutationNote: "structural: order sections for how a reviewer actually reads",
    fitness: 0.96,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(14),
    killedAt: isoDaysAgo(7),
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "ACC/AHA 2023 §3.2",
      "Internal precedent ×2",
    ],
  },
  {
    id: "bc_ae_017",
    cell: "aetna_cardiac",
    generation: 8,
    parentId: "bc_ae_013",
    label: "L8.b — statutory deadline",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3.b compliance. Cite the statutory turnaround deadline for expedited appeals and demand a decision within it, on the theory that procedural pressure speeds approval.",
    mutationNote: "add pressure: statutory expedited-appeal deadline demand",
    fitness: 0.89,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(14),
    killedAt: isoDaysAgo(8),
    citations: ["Aetna CPB 0228 §IV.A.3.b", "State expedited-appeal statute"],
  },
  {
    id: "bc_ae_018",
    cell: "aetna_cardiac",
    generation: 9,
    parentId: "bc_ae_016",
    label: "L9 — champion synthesis",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3.b compliance, sequenced for reviewer cognition: controlling sub-clause first, quantitative symptom table second, two de-identified prior overturns third, ACC/AHA 2023 §3.2 cross-cite fourth. Use 'medically necessary' verbatim ×6. Preempt the three secondary denial reasons with affirmative exhibits A, B, C. Close with a signed attending-physician credential block — NPI, state license, board certification.",
    mutationNote:
      "champion: reviewer-ordered synthesis + signed physician credential close",
    fitness: 0.98,
    tag: "production",
    status: "champion",
    createdAt: isoDaysAgo(7),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "ACC/AHA 2023 §3.2",
      "Internal precedent ×2",
      "Physician NPI + state license",
    ],
  },
  {
    id: "bc_ae_019",
    cell: "aetna_cardiac",
    generation: 9,
    parentId: "bc_ae_016",
    label: "L9.b — concise reviewer variant",
    promptBody:
      "The champion synthesis, trimmed to two pages: controlling sub-clause, the table, one precedent, the credential block. Drops the second precedent and the ACC/AHA cross-cite to fit a reviewer's attention budget.",
    mutationNote: "compression: two-page variant of the champion",
    fitness: 0.95,
    tag: "production",
    status: "alive",
    createdAt: isoDaysAgo(7),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "Internal precedent ×1",
      "Physician NPI + state license",
    ],
  },
  {
    id: "bc_ae_020",
    cell: "aetna_cardiac",
    generation: 9,
    parentId: "bc_ae_016",
    label: "L9.c — minimal-edit refinement",
    promptBody:
      "The champion synthesis with one change: the credential block moves above the exhibits so the reviewer sees physician authority before the evidence. Everything else is held constant to isolate the effect.",
    mutationNote: "ablation: lift the credential block above the exhibits",
    fitness: 0.93,
    tag: "experimental",
    status: "alive",
    createdAt: isoDaysAgo(7),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "ACC/AHA 2023 §3.2",
      "Physician NPI + state license",
    ],
  },
];

const aetnaFitness: FitnessPoint[] = [
  { generation: 0, meanFitness: 0.4, maxFitness: 0.4, survivingCount: 1, apoptosisCount: 0 },
  { generation: 1, meanFitness: 0.49, maxFitness: 0.55, survivingCount: 2, apoptosisCount: 1 },
  { generation: 2, meanFitness: 0.605, maxFitness: 0.63, survivingCount: 2, apoptosisCount: 2 },
  { generation: 3, meanFitness: 0.6, maxFitness: 0.71, survivingCount: 2, apoptosisCount: 4 },
  { generation: 4, meanFitness: 0.72, maxFitness: 0.78, survivingCount: 2, apoptosisCount: 6 },
  { generation: 5, meanFitness: 0.815, maxFitness: 0.84, survivingCount: 2, apoptosisCount: 8 },
  { generation: 6, meanFitness: 0.86, maxFitness: 0.9, survivingCount: 2, apoptosisCount: 10 },
  { generation: 7, meanFitness: 0.89, maxFitness: 0.94, survivingCount: 3, apoptosisCount: 12 },
  { generation: 8, meanFitness: 0.925, maxFitness: 0.96, survivingCount: 2, apoptosisCount: 15 },
  { generation: 9, meanFitness: 0.953, maxFitness: 0.98, survivingCount: 3, apoptosisCount: 17 },
];

const aetnaDenial: Denial = {
  id: "dn_ae_2026_05_25",
  cell: "aetna_cardiac",
  payer: "Aetna",
  diagnosis: "I25.10 — Atherosclerotic heart disease, native coronary artery",
  reasonCode: "CPB-0228-NM",
  body:
    "Coverage denied. Member's submitted documentation does not establish medical necessity per Aetna Clinical Policy Bulletin 0228, Section IV.A. Symptom duration and step-therapy progression are not demonstrated. Member may submit additional documentation within 60 days.",
  receivedAt: isoDaysAgo(7),
};

const aetnaRounds: TournamentRound[] = [
  {
    id: "rd_ae_g9",
    cell: "aetna_cardiac",
    generation: 9,
    denialId: aetnaDenial.id,
    candidateIds: ["bc_ae_018", "bc_ae_019", "bc_ae_020"],
    winnerId: "bc_ae_018",
    loserIds: ["bc_ae_019", "bc_ae_020"],
    judgeRationale:
      "L9 wins on completeness without bloat: it keeps both prior overturns and the ACC/AHA cross-cite that the concise variant (L9.b) drops, and it leads with the controlling §IV.A.3.b sub-clause — which the minimal-edit ablation (L9.c) buries beneath the credential block. All three clear 0.93; L9 reaches 0.98 because every secondary denial reason is affirmatively preempted and the physician credential block closes with reviewer-equivalent authority.",
    ranAt: isoDaysAgo(7),
  },
];

const aetnaMeta: CellMeta = {
  id: "aetna_cardiac",
  payer: "Aetna",
  diagnosis: "Cardiac diagnostic imaging",
  baselineOverturn: 0.4,
  currentOverturn: 0.98,
  generations: 10,
  populationSize: 3,
  apoptosisTotal: 18,
};

// ---------- Other cells (compact — a single maturing lineage each) ----------

const compactCell = (
  cell: CellId,
  payer: string,
  diagnosis: string,
  baseline: number,
  current: number,
  generations: number,
): CellPayload => {
  const strategies: BCellStrategy[] = Array.from({ length: generations + 1 }, (_, g) => {
    const isChampion = g === generations;
    const isTomb = g < generations - 1;
    const fitness = baseline + (current - baseline) * (g / generations);
    return {
      id: `bc_${cell.slice(0, 2)}_${String(g).padStart(3, "0")}`,
      cell,
      generation: g,
      parentId: g === 0 ? null : `bc_${cell.slice(0, 2)}_${String(g - 1).padStart(3, "0")}`,
      label: g === 0 ? "L0 — baseline" : `L${g} — gen ${g}`,
      promptBody: `Generation ${g} strategy for ${payer} ${diagnosis} appeals. (mock body)`,
      mutationNote: g === 0 ? null : `gen-${g} mutation`,
      fitness,
      tag: isChampion ? "production" : g === generations - 1 ? "production" : "experimental",
      status: isChampion ? "champion" : isTomb ? "tombstoned" : "alive",
      createdAt: isoDaysAgo(42 - g * 7),
      killedAt: isTomb ? isoDaysAgo(35 - g * 7) : null,
      citations: [`${payer} clinical policy bulletin (mock)`],
    };
  });

  const fitness: FitnessPoint[] = strategies.map((s, i) => ({
    generation: s.generation,
    meanFitness: s.fitness * 0.95,
    maxFitness: s.fitness,
    survivingCount: i === strategies.length - 1 ? 2 : 1,
    apoptosisCount: Math.max(0, i - 1),
  }));

  return {
    meta: {
      id: cell,
      payer,
      diagnosis,
      baselineOverturn: baseline,
      currentOverturn: current,
      generations,
      populationSize: 2,
      apoptosisTotal: Math.max(0, generations - 2),
    },
    strategies,
    rounds: [],
    fitness,
  };
};

// ---------- Public API ----------

export const ALL_CELLS: Record<CellId, CellPayload> = {
  aetna_cardiac: {
    meta: aetnaMeta,
    strategies: aetnaStrategies,
    rounds: aetnaRounds,
    fitness: aetnaFitness,
  },
  united_oncology: compactCell(
    "united_oncology",
    "UnitedHealthcare",
    "Oncology biomarker testing",
    0.38,
    0.72,
    5,
  ),
  anthem_mental_health: compactCell(
    "anthem_mental_health",
    "Anthem",
    "Residential mental-health",
    0.33,
    0.68,
    4,
  ),
  cigna_ortho: compactCell("cigna_ortho", "Cigna", "Knee arthroplasty", 0.45, 0.74, 5),
  humana_endocrinology: compactCell(
    "humana_endocrinology",
    "Humana",
    "Continuous glucose monitor (T2D)",
    0.51,
    0.81,
    4,
  ),
};

export const CELL_LIST: CellId[] = [
  "aetna_cardiac",
  "united_oncology",
  "anthem_mental_health",
  "cigna_ortho",
  "humana_endocrinology",
];

export const CELL_LABEL: Record<CellId, string> = {
  aetna_cardiac: "Aetna · Cardiac",
  united_oncology: "United · Oncology",
  anthem_mental_health: "Anthem · Mental Health",
  cigna_ortho: "Cigna · Orthopedic",
  humana_endocrinology: "Humana · Endocrinology",
};

export function getCell(id: CellId): CellPayload {
  return ALL_CELLS[id];
}

export const titleCase = (s: string): string =>
  s.replace(/\b\w/g, (c) => c.toUpperCase());

/**
 * Display label for a cell. Prefers the curated CELL_LABEL; falls back to a
 * title-cased "Payer · Diagnosis" for any cell the live API serves that the
 * static map doesn't know about. Keeps the nav honest to what the API returns.
 */
export function cellLabelFromMeta(meta: {
  id: CellId;
  payer: string;
  diagnosis: string;
}): string {
  return CELL_LABEL[meta.id] ?? `${titleCase(meta.payer)} · ${titleCase(meta.diagnosis)}`;
}

// ---------- Co-evolution mock (dual tree) ----------

export function getCoEvolution(cell: CellId): CoEvolutionState {
  const payload = getCell(cell);
  // Mirror writer strategies into a payer "adversary" population — same shape,
  // different mutation notes, fitness inverted from the writers' perspective.
  const payers: BCellStrategy[] = payload.strategies.map((s) => ({
    ...s,
    id: `pa_${s.id.slice(3)}`,
    label: `Payer-${s.label}`,
    promptBody: `Adversarial payer denial template (gen ${s.generation}).`,
    mutationNote: s.mutationNote ? `payer-counter: ${s.mutationNote}` : null,
    fitness: 1 - s.fitness,
  }));
  return { cell, writers: payload.strategies, payers };
}
