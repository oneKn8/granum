"""Granum FastAPI — serves the real CellPayload artifacts to the Next.js frontend.

Implements the contract in `docs/api-contract.md` / `web/lib/api.ts`:
  GET /api/cells                       -> { "cells": CellMeta[] }
  GET /api/cells/{cell}                -> CellPayload
  GET /api/cells/{cell}/coevolution    -> CoEvolutionState (404 until live data)

Data source is a directory of `{cell}.json` payloads produced by `granum evolve`
(`GRANUM_DATA_DIR`, default `runs/cell_payloads`). The API is intentionally a
thin static server over those artifacts — no live Phoenix/MCP dependency at
request time, so it deploys cleanly to Cloud Run.

Run locally:
    env -u PYTHONPATH uv run uvicorn granum.web.api:app --port 8000
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Granum API", version="0.1.0")

# Single-tenant demo: allow the Next.js origin (configurable) to read.
_origins = os.getenv("GRANUM_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _data_dir() -> Path:
    # Read at call time so tests can point it elsewhere via env.
    return Path(os.getenv("GRANUM_DATA_DIR", "runs/cell_payloads"))


def _load(cell: str) -> dict | None:
    f = _data_dir() / f"{cell}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "dataDir": str(_data_dir())}


@app.get("/api/cells")
def list_cells() -> dict:
    cells: list[dict] = []
    for f in sorted(_data_dir().glob("*.json")):
        if f.name.endswith("_coevolution.json"):
            continue
        try:
            cells.append(json.loads(f.read_text())["meta"])
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return {"cells": cells}


@app.get("/api/cells/{cell}")
def get_cell(cell: str) -> dict:
    payload = _load(cell)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"cell {cell!r} has no evolution data")
    return payload


@app.get("/api/cells/{cell}/coevolution")
def get_coevolution(cell: str) -> dict:
    """Co-evolution (Red Queen) state for a cell.

    Returns an EMPTY-but-valid CoEvolutionState when no live co-evolution run
    exists yet (the common case) rather than a 404 — the frontend's cell page
    fetches this unconditionally and treats a non-200 as a fatal error.
    """
    f = _data_dir() / f"{cell}_coevolution.json"
    if not f.exists():
        return {"cell": cell, "writers": [], "payers": []}
    return json.loads(f.read_text())
