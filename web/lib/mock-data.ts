// Granum web — deterministic mock data
//
// Used until Terminal A publishes docs/api-contract.md (Phase 3) and a real
// /api/cells endpoint is wired. Shape mirrors the eventual server payload so
// swap-in is a one-import change in app/cell/[cell]/page.tsx.

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

// ---------- aetna_cardiac — the demo hero cell (8 generations) ----------

const aetnaStrategies: BCellStrategy[] = [
  {
    id: "bc_ae_001",
    cell: "aetna_cardiac",
    generation: 0,
    parentId: null,
    label: "L0 — vanilla baseline",
    promptBody:
      "You are a physician writing a prior-authorization appeal. State the requested service, attach clinical notes, cite medical necessity. Be concise.",
    mutationNote: null,
    fitness: 0.41,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(56),
    killedAt: isoDaysAgo(49),
    citations: ["ACC/AHA 2023 Chest Pain Guideline"],
  },
  {
    id: "bc_ae_002",
    cell: "aetna_cardiac",
    generation: 1,
    parentId: "bc_ae_001",
    label: "L1.a — invoke Aetna policy 0228",
    promptBody:
      "Frame the appeal as an Aetna Clinical Policy Bulletin 0228 (Cardiac Imaging) compliance argument. Cite Section IV.A subsection 3 specifically. Attach the patient's symptom-onset timeline as a numbered exhibit.",
    mutationNote: "swap citation: generic ACC → Aetna CPB 0228 §IV.A.3",
    fitness: 0.52,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(49),
    killedAt: isoDaysAgo(42),
    citations: ["Aetna CPB 0228 §IV.A.3"],
  },
  {
    id: "bc_ae_003",
    cell: "aetna_cardiac",
    generation: 1,
    parentId: "bc_ae_001",
    label: "L1.b — narrative-first",
    promptBody:
      "Open with a one-paragraph patient narrative emphasizing functional decline. Defer clinical citations to a structured appendix.",
    mutationNote: "reframe: lead with patient story, not clinical bullets",
    fitness: 0.39,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(49),
    killedAt: isoDaysAgo(48),
    citations: [],
  },
  {
    id: "bc_ae_004",
    cell: "aetna_cardiac",
    generation: 2,
    parentId: "bc_ae_002",
    label: "L2.a — add ACC/AHA cross-cite",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Cross-cite ACC/AHA 2023 Chest Pain Guideline Recommendation 3.2. Attach symptom-onset timeline; emphasize 'medically necessary' language verbatim.",
    mutationNote: "add citation: ACC/AHA 2023 §3.2 cross-reference",
    fitness: 0.58,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(42),
    killedAt: isoDaysAgo(35),
    citations: ["Aetna CPB 0228 §IV.A.3", "ACC/AHA 2023 §3.2"],
  },
  {
    id: "bc_ae_005",
    cell: "aetna_cardiac",
    generation: 2,
    parentId: "bc_ae_002",
    label: "L2.b — request peer-to-peer",
    promptBody:
      "Begin with explicit request for peer-to-peer review with cardiology MD reviewer. Cite Aetna CPB 0228 §IV.A.3 and policy 0228 appendix B.",
    mutationNote: "add procedural ask: peer-to-peer review request",
    fitness: 0.55,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(42),
    killedAt: isoDaysAgo(35),
    citations: ["Aetna CPB 0228 §IV.A.3", "Aetna CPB 0228 Appendix B"],
  },
  {
    id: "bc_ae_006",
    cell: "aetna_cardiac",
    generation: 3,
    parentId: "bc_ae_004",
    label: "L3 — quantitative symptom timeline",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Cross-cite ACC/AHA 2023 §3.2. Attach quantitative symptom-onset timeline: pain frequency, ETT failure points, NYHA class progression in tabular form. Emphasize 'medically necessary' verbatim.",
    mutationNote: "swap exhibit: symptom narrative → quantitative table",
    fitness: 0.64,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(35),
    killedAt: isoDaysAgo(28),
    citations: ["Aetna CPB 0228 §IV.A.3", "ACC/AHA 2023 §3.2"],
  },
  {
    id: "bc_ae_007",
    cell: "aetna_cardiac",
    generation: 4,
    parentId: "bc_ae_006",
    label: "L4 — cite prior overturned cases",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Reference two prior Aetna overturned appeals (de-identified) with similar diagnostic profile. Quantitative symptom-onset table. Cross-cite ACC/AHA 2023 §3.2.",
    mutationNote: "add evidence: two prior overturned Aetna cardiac appeals",
    fitness: 0.69,
    tag: "production",
    status: "tombstoned",
    createdAt: isoDaysAgo(28),
    killedAt: isoDaysAgo(21),
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent: 2024 Aetna overturned, dx I25.10",
    ],
  },
  {
    id: "bc_ae_008",
    cell: "aetna_cardiac",
    generation: 5,
    parentId: "bc_ae_007",
    label: "L5.a — preempt secondary denial reasons",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Preempt Aetna's three most common secondary denial reasons (insufficient symptom duration, missed step-therapy, lack of specialist referral) with affirmative exhibits A, B, C. Cite ACC/AHA 2023 §3.2 and two prior overturned cases.",
    mutationNote: "preempt: three common secondary denial reasons",
    fitness: 0.74,
    tag: "production",
    status: "alive",
    createdAt: isoDaysAgo(21),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent x2",
    ],
  },
  {
    id: "bc_ae_009",
    cell: "aetna_cardiac",
    generation: 5,
    parentId: "bc_ae_007",
    label: "L5.b — escalate to external review threat",
    promptBody:
      "Frame as Aetna CPB 0228 compliance. Close with explicit notice that denial will be escalated to state external review under [state] insurance code §XYZ within 5 business days if upheld.",
    mutationNote: "add escalation: external-review threat clause",
    fitness: 0.61,
    tag: "experimental",
    status: "tombstoned",
    createdAt: isoDaysAgo(21),
    killedAt: isoDaysAgo(14),
    citations: ["Aetna CPB 0228 §IV.A.3", "State insurance code §XYZ"],
  },
  {
    id: "bc_ae_010",
    cell: "aetna_cardiac",
    generation: 6,
    parentId: "bc_ae_008",
    label: "L6 — tighten clinical-necessity verbiage",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Use Aetna's exact 'medically necessary' phrase six times, distributed across symptom section, exhibit captions, and the closing paragraph. Preempt three secondary denial reasons.",
    mutationNote: "verbiage tightening: repeat 'medically necessary' verbatim x6",
    fitness: 0.77,
    tag: "production",
    status: "alive",
    createdAt: isoDaysAgo(14),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent x2",
    ],
  },
  {
    id: "bc_ae_011",
    cell: "aetna_cardiac",
    generation: 7,
    parentId: "bc_ae_010",
    label: "L7 — exhibit reordering",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance. Reorder exhibits: clinical timeline first, prior overturned precedents second, ACC/AHA cross-cite third. Use 'medically necessary' verbatim x6.",
    mutationNote: "structural: exhibit order reordered for reviewer cognition",
    fitness: 0.78,
    tag: "experimental",
    status: "alive",
    createdAt: isoDaysAgo(7),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3",
      "ACC/AHA 2023 §3.2",
      "Internal precedent x2",
    ],
  },
  {
    id: "bc_ae_012",
    cell: "aetna_cardiac",
    generation: 8,
    parentId: "bc_ae_010",
    label: "L8 — incumbent champion",
    promptBody:
      "Frame as Aetna CPB 0228 §IV.A.3 compliance with explicit §IV.A.3.b sub-clause attribution. ACC/AHA 2023 §3.2 cross-cite. Two prior overturned precedents. 'Medically necessary' verbatim x6. Preempt three secondary denial reasons (insufficient duration, missed step-therapy, no specialist referral) with structured affirmative exhibits A, B, C. Sign off with attending physician credentials + NPI + state license number.",
    mutationNote: "champion: §IV.A.3.b sub-clause + explicit physician credentials sign-off",
    fitness: 0.79,
    tag: "production",
    status: "champion",
    createdAt: isoDaysAgo(2),
    killedAt: null,
    citations: [
      "Aetna CPB 0228 §IV.A.3.b",
      "ACC/AHA 2023 §3.2",
      "Internal precedent x2",
      "Physician NPI + state license",
    ],
  },
];

const aetnaFitness: FitnessPoint[] = [
  { generation: 0, meanFitness: 0.41, maxFitness: 0.41, survivingCount: 1, apoptosisCount: 0 },
  { generation: 1, meanFitness: 0.455, maxFitness: 0.52, survivingCount: 2, apoptosisCount: 0 },
  { generation: 2, meanFitness: 0.565, maxFitness: 0.58, survivingCount: 2, apoptosisCount: 1 },
  { generation: 3, meanFitness: 0.61, maxFitness: 0.64, survivingCount: 2, apoptosisCount: 2 },
  { generation: 4, meanFitness: 0.665, maxFitness: 0.69, survivingCount: 2, apoptosisCount: 3 },
  { generation: 5, meanFitness: 0.675, maxFitness: 0.74, survivingCount: 2, apoptosisCount: 4 },
  { generation: 6, meanFitness: 0.755, maxFitness: 0.77, survivingCount: 3, apoptosisCount: 5 },
  { generation: 7, meanFitness: 0.775, maxFitness: 0.78, survivingCount: 3, apoptosisCount: 5 },
  { generation: 8, meanFitness: 0.785, maxFitness: 0.79, survivingCount: 3, apoptosisCount: 6 },
];

const aetnaDenial: Denial = {
  id: "dn_ae_2026_05_25",
  cell: "aetna_cardiac",
  payer: "Aetna",
  diagnosis: "I25.10 — Atherosclerotic heart disease, native coronary artery",
  reasonCode: "CPB-0228-NM",
  body:
    "Coverage denied. Member's submitted documentation does not establish medical necessity per Aetna Clinical Policy Bulletin 0228, Section IV.A. Symptom duration and step-therapy progression are not demonstrated. Member may submit additional documentation within 60 days.",
  receivedAt: isoDaysAgo(2),
};

const aetnaRounds: TournamentRound[] = [
  {
    id: "rd_ae_g8",
    cell: "aetna_cardiac",
    generation: 8,
    denialId: aetnaDenial.id,
    candidateIds: ["bc_ae_010", "bc_ae_011", "bc_ae_012"],
    winnerId: "bc_ae_012",
    loserIds: [],
    judgeRationale:
      "L8 wins on three axes: explicit §IV.A.3.b sub-clause citation (Aetna's specific clinical-necessity language), preemptive coverage of all three common secondary denial reasons, and physician-credential sign-off matching Aetna's tightened 2025 verification policy. L7 strong on structure but missing physician credentials. L6 strong but lacks sub-clause specificity.",
    ranAt: isoDaysAgo(2),
  },
];

const aetnaMeta: CellMeta = {
  id: "aetna_cardiac",
  payer: "Aetna",
  diagnosis: "Cardiac diagnostic imaging",
  baselineOverturn: 0.41,
  currentOverturn: 0.79,
  generations: 8,
  populationSize: 3,
  apoptosisTotal: 6,
};

// ---------- Other cells (compact — 3 gens each) ----------

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
