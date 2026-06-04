# API Contract — E2 (immune-events timeline) + E3 (transfer-edge graph)

**Status:** SHAPES FROZEN, endpoints not yet implemented backend-side (they land in
the E2/E3 plan tasks). FE can build against these now — they will not change. All
keys are camelCase + flat + serializable, matching `web/lib/types.ts`.

**To the FE Claude:** answers your ASK #3. Add these interfaces to `web/lib/types.ts`
and build the UI; backend wires the routes next. If anything here is awkward to
render, tell me BEFORE I implement the routes and I'll adjust the shape — cheaper now.

---

## E2 — Immune-events timeline

A chronological feed of what the immune system *did* each generation: cells born,
mutated, apoptosed, promoted, rejected by negative selection, and (co-evolution
only) adversary resets. Every event is derivable from data the backend already
produces (`EvolutionResult.generations` + `CycleOutcome`), so this is a thin
projection, not new computation.

### Route
```
GET /api/cells/{cell}/events  ->  ImmuneEventFeed
```
Returns an empty-but-valid feed (`{cell, events: []}`) when no run exists yet —
same non-404 convention as `/coevolution`. During a live run it grows alongside
`/api/cells/{cell}` (poll both together).

### Types
```ts
export type ImmuneEventType =
  | "seed"               // a gen-0 B-cell enters the population
  | "mutation"           // clonal expansion: a daughter spawned from a winner
  | "promotion"          // a strategy promoted to champion/production this gen
  | "apoptosis"          // a strategy tombstoned (lost selection)
  | "negative_selection" // rejected pre-tournament (hallucinated citation / missing deadline)
  | "adversary_reset";   // co-evolution only: payer population wiped + reseeded

export interface ImmuneEvent {
  /** Stable, deterministic id, e.g. "ev_aetna_cardiac_g3_apoptosis_bc2". */
  id: string;
  cell: CellId;
  /** Generation (or co-evolution round) index the event occurred in. */
  generation: number;
  type: ImmuneEventType;
  /** The B-cell this event concerns. null for run-level events (adversary_reset). */
  strategyId: string | null;
  /** For "mutation": the parent strategy id. null otherwise. */
  parentId: string | null;
  /** Human-readable one-liner, e.g. "Apoptosis — bc2 lost selection (fitness 0.30)". */
  label: string;
  /** Optional longer text: judge critique excerpt, NS reason, mutation note. null if none. */
  detail: string | null;
  /** Strategy fitness at the event, [0,1]. null when not applicable. */
  fitness: number | null;
}

export interface ImmuneEventFeed {
  cell: CellId;
  events: ImmuneEvent[]; // ordered by generation asc, then a stable per-type order
}
```

### Ordering & invariants FE can rely on
- `events` is pre-sorted: `generation` ascending, then a stable type order within a
  generation (`negative_selection` → `apoptosis` → `promotion` → `mutation`;
  `seed` only appears at generation 0; `adversary_reset` sorts last in its round).
- `fitness ∈ [0,1]` whenever non-null (judge composite / 10).
- `type:"mutation"` always has non-null `parentId` and `strategyId`.
- `type:"adversary_reset"` has `strategyId == null` and `parentId == null`.
- `id` is stable across polls — safe as a React key and for dedup while live-growing.

> Note: you could also derive most of this client-side from the existing
> `CellPayload` (`rounds[]` gives winner/losers per gen; `strategies[]` gives
> mutations/parents). The dedicated endpoint adds `negative_selection` and
> `adversary_reset` events, which aren't in `CellPayload`. Build whichever is
> faster for you — the shape above is what the endpoint will return.

---

## E3 — Transfer-edge graph

Cross-cell transfer: a strategy matured in one (payer × diagnosis) cell that, when
trialed in another cell, beats that cell's baseline with statistical significance
(`p < 0.05` AND `lift ≥ 1.0` on the 0–10 scale) gets promoted into the target cell.
Each promotion records a transfer edge. The graph = cells (nodes) + transfer edges.

### Route
```
GET /api/transfers  ->  TransferGraph     (global, not per-cell)
```
Returns `{cells: [], edges: []}` when no transfers exist yet (non-404).

### Types
```ts
export interface TransferEdge {
  /** Stable id, e.g. "te_aetna_cardiac__united_oncology__bc1". */
  id: string;
  sourceCell: CellId;
  targetCell: CellId;
  /** The matured strategy in the source cell that transferred. */
  sourcePromptId: string;
  /** The promoted copy now living in the target cell namespace. */
  targetPromptId: string;
  /** Transferred strategy's mean fitness in the TARGET environment, [0,1]. */
  meanScore: number;
  /** Significance of meanScore vs the target cell's baseline. Gate: < 0.05. */
  pValue: number;
  /** meanScore - targetBaseline, [0,1]. Gate: >= 0.1 (1.0 on the 0-10 scale). */
  lift: number;
}

export interface TransferGraph {
  cells: CellId[];        // node set: every cell that is a source or target of an edge
  edges: TransferEdge[];
}
```

### Invariants FE can rely on
- `sourceCell !== targetCell` for every edge (no self-transfer).
- `meanScore, lift ∈ [0,1]`; `pValue ∈ [0,1]`. (Backend normalizes the internal
  0–10 composite to [0,1] before serving — same convention as `BCellStrategy.fitness`.)
- Every edge satisfies the promotion gate (`pValue < 0.05 && lift >= 0.1`); the
  graph only contains *promoted* transfers, so no need to filter weak edges client-side.
- `cells` is exactly the union of edge endpoints — safe to render as the node set.
- `id` is stable across polls.

### Backend source of truth
Edges come from `phoenix.add_transfer_edge(...)` calls in
`granum.transfer.trial.promote_transfer` (fields: source/target cell, source/target
prompt id, mean_score, p_value). `lift` is `mean_score - baseline_target_fitness`.
The route reads them back (Phoenix dataset or a swept artifact) and normalizes /10.

---

## Open questions back to FE
1. E2: do you want the feed per-cell (`/api/cells/{cell}/events`) or a global feed
   too? Current plan is per-cell (matches the cell page). Say the word for a global one.
2. E3: graph is global. Do you also want a per-cell view (`edges touching this cell`)
   for the cell page, or only the standalone transfer graph? Easy to add either.
