// Granum API client.
//
// Behind a feature flag so the demo runs against deterministic mock data
// until Cloud Run + Phoenix Cloud are wired (Phase 0.5 + 1.10 — gated on
// GCP billing + ADC + Phoenix API key).
//
// Flag:
//   NEXT_PUBLIC_USE_REAL_API=true  → fetch from NEXT_PUBLIC_API_BASE_URL
//   NEXT_PUBLIC_USE_REAL_API=false → use mock-data.ts (default)
//
// Contract: docs/api-contract.md v0.1 (Terminal A).
// Endpoints: GET /api/cells, GET /api/cells/{cell}, GET /api/cells/{cell}/coevolution.

import {
  ALL_CELLS,
  CELL_LIST,
  getCell as getMockCell,
  getCoEvolution as getMockCoEvolution,
} from "./mock-data";
import type { CellId, CellMeta, CellPayload, CoEvolutionState } from "./types";

const USE_REAL_API =
  process.env.NEXT_PUBLIC_USE_REAL_API === "true" ||
  process.env.NEXT_PUBLIC_USE_REAL_API === "1";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

class ApiError extends Error {
  constructor(public status: number, public problem: unknown, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      0,
      null,
      "NEXT_PUBLIC_API_BASE_URL is not set; cannot fetch real API.",
    );
  }
  const url = `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  // Server components run this at request time on the server; cache: "no-store"
  // is intentional so demo always reflects the latest Phoenix state. Bump to
  // ISR (revalidate: 60) once the dataset stabilizes.
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    let problem: unknown = null;
    try {
      problem = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(
      res.status,
      problem,
      `GET ${path} → ${res.status} ${res.statusText}`,
    );
  }
  return (await res.json()) as T;
}

// ---------- Public client ----------

export async function listCellMetas(): Promise<CellMeta[]> {
  if (USE_REAL_API) {
    const data = await fetchJson<{ cells: CellMeta[] }>("/api/cells");
    return data.cells;
  }
  return CELL_LIST.map((id) => ALL_CELLS[id].meta);
}

export async function getCellPayload(cell: CellId): Promise<CellPayload> {
  if (USE_REAL_API) {
    return fetchJson<CellPayload>(`/api/cells/${cell}`);
  }
  return getMockCell(cell);
}

export async function getCoEvolution(
  cell: CellId,
): Promise<CoEvolutionState> {
  if (USE_REAL_API) {
    return fetchJson<CoEvolutionState>(`/api/cells/${cell}/coevolution`);
  }
  return getMockCoEvolution(cell);
}

export function isRealApiEnabled(): boolean {
  return USE_REAL_API;
}

export { ApiError };
