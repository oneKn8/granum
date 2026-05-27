# Granum API Contract

**Status:** v0.1 — locked 2026-05-27, Phase 3 prep
**Producer:** Terminal A (`src/granum/web/api.py`, to land in Phase 3 wiring)
**Consumer:** Terminal C frontend (`web/lib/` — swap `mock-data.ts` for fetcher)

This document is the source of truth for the JSON shapes the FastAPI server will return. Terminal C's `web/lib/types.ts` is the canonical TypeScript representation; this file mirrors those types and lists the endpoints that produce them.

---

## Type alignment

The Python `dataclass` definitions in `src/granum/` map onto Terminal C's `web/lib/types.ts` interfaces 1:1, with a small naming normalization layer in the FastAPI response models (Pydantic `BaseModel` with `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`). Python uses `snake_case`; JSON over the wire is `camelCase` to match TypeScript convention.

| TypeScript (web/lib/types.ts) | Python source | Notes |
|---|---|---|
| `BCellStrategy` | `granum.tools.phoenix_client.PromptVersion` + computed lineage metadata | enriched server-side from Phoenix prompt registry + cycle.py outputs |
| `Denial` | `granum.data.denials.Denial` | direct mapping; `receivedAt` derived from `submission_date` |
| `TournamentRound` | `granum.center.tournament.TournamentResult` | enriched with `denialId` from the cycle that ran it |
| `FitnessPoint` | aggregated from dataset `granum/<cell>/outcomes` | computed per generation server-side |
| `CellMeta` | `granum.center.cell.Cell` + computed totals | summary doc per cell |
| `CellPayload` | bundle for one cell view | composed in `/api/cells/{cell}` endpoint |
| `CoEvolutionState` | NEW in Phase 3 | two populations: appeal-writers + payer-adversaries |

---

## Endpoints

All endpoints are JSON, GET, no auth in v0.1 (single-tenant demo). Base URL is the Cloud Run service URL once Phase 0.5 deploys.

### `GET /api/cells`

List of all validated cells with summary metadata.

**Response shape:**

```json
{
  "cells": [
    {
      "id": "aetna_cardiac",
      "payer": "aetna",
      "diagnosis": "cardiac",
      "baselineOverturn": 0.41,
      "currentOverturn": 0.79,
      "generations": 8,
      "populationSize": 5,
      "apoptosisTotal": 17
    },
    ...
  ]
}
```

**Source:** `granum.center.cell.CellRegistry.validated_cells()` + dataset aggregation per cell.

---

### `GET /api/cells/{cell}`

Full payload for one cell view — strategies (full lineage), rounds, fitness curve.

**Response shape:** matches `CellPayload`:

```json
{
  "meta": {
    "id": "aetna_cardiac",
    "payer": "aetna",
    "diagnosis": "cardiac",
    "baselineOverturn": 0.41,
    "currentOverturn": 0.79,
    "generations": 8,
    "populationSize": 5,
    "apoptosisTotal": 17
  },
  "strategies": [
    {
      "id": "bc_ae_001",
      "cell": "aetna_cardiac",
      "generation": 0,
      "parentId": null,
      "label": "L0 — vanilla baseline",
      "promptBody": "...",
      "mutationNote": null,
      "fitness": 0.41,
      "tag": "production",
      "status": "tombstoned",
      "createdAt": "2026-04-01T15:00:00Z",
      "killedAt": "2026-04-08T15:00:00Z",
      "citations": ["..."]
    },
    ...
  ],
  "rounds": [
    {
      "id": "tr_xxx",
      "cell": "aetna_cardiac",
      "generation": 3,
      "denialId": "aetna_cardiac_a1b2c3",
      "candidateIds": ["bc_ae_004", "bc_ae_005", "bc_ae_006"],
      "winnerId": "bc_ae_005",
      "loserIds": ["bc_ae_004", "bc_ae_006"],
      "judgeRationale": "Strategy 005 cited CPB 0286 §III directly with the precise step-therapy clause...",
      "ranAt": "2026-04-15T12:00:00Z"
    },
    ...
  ],
  "fitness": [
    {"generation": 0, "meanFitness": 0.41, "maxFitness": 0.41, "survivingCount": 3, "apoptosisCount": 0},
    {"generation": 1, "meanFitness": 0.46, "maxFitness": 0.52, "survivingCount": 4, "apoptosisCount": 1},
    ...
  ]
}
```

**Source mapping per field:**

- `meta`: as in `/api/cells` for this cell
- `strategies`: enumerate Phoenix prompt versions where `name LIKE '{cell}/%'`. For each:
  - `id`: Phoenix `promptId`
  - `generation`: parsed from prompt name (e.g., `aetna_cardiac/bcell_mut_X_Y` → generation N)
  - `parentId`: parsed from prompt name (the X in `bcell_mut_X_Y`)
  - `label`: synthesized server-side: `"L{gen}.{idx} — {mutation kind}"`
  - `promptBody`: the version body
  - `mutationNote`: derived from the mutation operator that produced this version (CITATION_SWAP target→replacement, PARAGRAPH_REFRAME target→replacement, etc.)
  - `fitness`: latest composite score in the outcomes dataset filtered by this prompt_id
  - `tag`: `"production"` if `production` tag present, else `"experimental"`
  - `status`: `"tombstoned"` if `tombstoned` tag present, `"champion"` if `production` tag and not tombstoned, else `"alive"`
  - `createdAt`: Phoenix version creation timestamp
  - `killedAt`: server-side metadata kept in the outcomes dataset
  - `citations`: extracted from `promptBody` via `granum.center.negative_selection.extract_citations`
- `rounds`: one entry per outcomes-dataset row for this cell
- `fitness`: aggregated per generation from outcomes dataset

---

### `GET /api/cells/{cell}/coevolution`

Two-population view introduced in Phase 3. Returns the appeal-writer population AND the adversarial payer-agent population for this cell.

**Response shape:** matches `CoEvolutionState`:

```json
{
  "cell": "aetna_cardiac",
  "writers": [
    /* same BCellStrategy shape as /api/cells/{cell}.strategies */
  ],
  "payers": [
    /* BCellStrategy shape; lineage of payer-adversary system prompts */
  ]
}
```

**Source:** Phoenix prompt registry queried with two name prefixes: `{cell}/` (writers) and `{cell}_payer/` (adversaries).

---

### `GET /api/cells/{cell}/denials`

Recent denials observed for this cell (used by the denial-stream visualization on the per-cell page).

**Response shape:**

```json
{
  "denials": [
    {
      "id": "aetna_cardiac_a1b2c3",
      "cell": "aetna_cardiac",
      "payer": "aetna",
      "diagnosis": "cardiac",
      "reasonCode": "not_medically_necessary",
      "body": "Coverage denied for echocardiogram (CPT 93306)...",
      "receivedAt": "2026-05-15T09:00:00Z"
    },
    ...
  ]
}
```

**Source:** synthetic denial generator in v0.1 (rolling log of last 50 generated denials); v0.2 will store these in SQLite.

---

### `GET /api/healthz`

Healthcheck. Returns `{"status": "ok"}`. Already exists from Phase 0.5 hello-world (will exist once GCP billing unblocks deploy).

---

## CamelCase ↔ snake_case

Python:
```python
class CellMetaDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    payer: str
    diagnosis: str
    baseline_overturn: float
    current_overturn: float
    generations: int
    population_size: int
    apoptosis_total: int
```

Serialized JSON:
```json
{
  "id": "aetna_cardiac",
  "payer": "aetna",
  "diagnosis": "cardiac",
  "baselineOverturn": 0.41,
  "currentOverturn": 0.79,
  "generations": 8,
  "populationSize": 5,
  "apoptosisTotal": 17
}
```

---

## Errors

All endpoints return RFC 7807 problem details on error:

```json
{
  "type": "https://granum.dev/probs/cell-not-found",
  "title": "Cell not found",
  "status": 404,
  "detail": "No declared cell with id 'foo_bar'."
}
```

Status codes used:
- `200` OK
- `404` Not found (unknown cell id)
- `503` Service unavailable (Phoenix client error — temporary)

---

## CORS

Cloud Run service allows GET from `https://*.vercel.app` (Terminal C's deployment target) and from `http://localhost:3000` for dev. Configured in `src/granum/web/app.py` via `CORSMiddleware`.

---

## Stability promises

- Field names: stable for v0.1.
- Adding new optional fields: non-breaking.
- Removing or renaming fields: breaking — requires bump to `/api/v2/`.
- v0.1 → v1.0 in scope: rename `bc_*` ids to UUID, add per-strategy `traceLink` (Phoenix trace URL).

---

## Outstanding

- Real fitness computation requires the live-cycle loop (Phase 1.10) to run with real Phoenix. Until then, the server can return synthesized data from the same generators Terminal C uses in `mock-data.ts`. **Recommendation for Terminal C**: keep `mock-data.ts` and add a feature flag `NEXT_PUBLIC_USE_REAL_API` that, when `true`, fetches from Cloud Run; when `false`, uses mock. This lets the demo work BEFORE Phase 0.5/1.10 unblock.
- `/api/cells/{cell}/coevolution` is Phase 3 work — Terminal A will publish this once the Red Queen population lands.
- `judgeRationale` field in `TournamentRound` is populated from the English-feedback channel of the LLM-as-judge (per `JudgeScore.english_feedback`).
