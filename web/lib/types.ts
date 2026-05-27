// Granum web — shared types
//
// This file is the mock-contract source-of-truth until Terminal A publishes
// docs/api-contract.md (Phase 3). When that drops, this file is what Terminal C
// diffs against. Keep shapes flat and serializable.

export type CellId =
  | "aetna_cardiac"
  | "united_oncology"
  | "anthem_mental_health"
  | "cigna_ortho"
  | "humana_endocrinology";

export type LineageStatus = "alive" | "tombstoned" | "champion";
export type LineageTag = "experimental" | "production";

export interface BCellStrategy {
  /** Stable hex-prefixed id, e.g. "bc_a1b2c3". */
  id: string;
  /** (payer × diagnosis) cell this strategy lives in. */
  cell: CellId;
  /** Zero-indexed generation. Gen 0 is the seeded baseline. */
  generation: number;
  /** id of the parent strategy this one mutated from. null for gen-0 seeds. */
  parentId: string | null;
  /** Human-readable lineage name, e.g. "L3.2 — clinical-necessity tightening". */
  label: string;
  /** Full system prompt body. */
  promptBody: string;
  /** Concise rationale of what this mutation changed vs parent. */
  mutationNote: string | null;
  /** Fitness on the gold dataset, [0, 1]. */
  fitness: number;
  /** Production / experimental promotion tag (Phoenix add-prompt-version-tag). */
  tag: LineageTag;
  /** Current lifecycle state. */
  status: LineageStatus;
  /** ISO timestamp. */
  createdAt: string;
  /** ISO timestamp; non-null iff status === "tombstoned". */
  killedAt: string | null;
  /** Citations the strategy preferentially cites (paragraph-level). */
  citations: string[];
}

export interface Denial {
  id: string;
  cell: CellId;
  payer: string;
  diagnosis: string;
  reasonCode: string;
  body: string;
  receivedAt: string;
}

export interface TournamentRound {
  id: string;
  cell: CellId;
  generation: number;
  denialId: string;
  candidateIds: string[];
  winnerId: string;
  loserIds: string[];
  judgeRationale: string;
  ranAt: string;
}

export interface FitnessPoint {
  generation: number;
  meanFitness: number;
  maxFitness: number;
  survivingCount: number;
  apoptosisCount: number;
}

export interface CellMeta {
  id: CellId;
  payer: string;
  diagnosis: string;
  /** Vanilla baseline overturn rate before any evolution. */
  baselineOverturn: number;
  /** Current best overturn rate (champion of latest generation). */
  currentOverturn: number;
  /** Number of generations completed. */
  generations: number;
  /** Number of strategies alive right now. */
  populationSize: number;
  /** Number of strategies tombstoned across all generations. */
  apoptosisTotal: number;
}

/** Bundle returned per cell view. */
export interface CellPayload {
  meta: CellMeta;
  strategies: BCellStrategy[];
  rounds: TournamentRound[];
  fitness: FitnessPoint[];
}

/** Co-evolution: appeal-writer population vs payer-adversary population. */
export interface CoEvolutionState {
  cell: CellId;
  writers: BCellStrategy[];
  payers: BCellStrategy[];
}
