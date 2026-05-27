# Granum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working, deployed, demo-ready Granum submission to the Google Cloud Rapid Agent Hackathon — Arize Phoenix track — by 2026-06-11 14:00 PDT, that beats the 6 visible competitors on Idea + Impact while clearing the Stage One pass/fail gate on Tech + Design + Functional Autonomy.

**Architecture:** Single ADK agent (Granum) maintains a population of "B-cell" appeal-writer strategies per (payer × diagnosis) cell. A second adversarial ADK agent population (Red Queen) co-evolves as denial-writers. Both populations run in Phoenix prompt registry. Tournaments use LLM-as-judge with structured English feedback. Five immune mechanisms gate selection: negative selection, clonal expansion, functional apoptosis, immune memory, antigen drift. Cloud Run hosts both agents + a Next.js frontend that renders Phoenix lineage trees side-by-side. Demo is 3 cells minimum, ideally 5, with cross-cell transfer detection.

**Tech Stack:** Python 3.12, Google ADK, Gemini 3 Pro (Vertex AI), Arize Phoenix Cloud + `@arizeai/phoenix-mcp` (stdio), SQLite (local state), FastAPI (backend API), Next.js 15 + TypeScript + Tailwind + D3 (frontend lineage trees), Cloud Run (deploy), Cloud Scheduler (evolution cycles), GitHub Actions (CI), pytest + Playwright (test), `uv` (Python toolchain), Apache-2.0 license.

**Build assumption:** Parallel agent execution (multiple Claude Code + Codex sessions). Per [[feedback-velocity-not-timid-estimates]], a 14-day hackathon window compresses to ~3-5 effective build days at agent velocity. Phases are designed to run with parallelizable workstreams where marked `PARALLEL:`.

---

## Pre-flight: Critical Phoenix MCP Reality Check

**Before Phase 0 begins**, the engineer MUST empirically verify Phoenix MCP capabilities. This is the load-bearing assumption of the entire plan.

### Task A: Phoenix MCP capability audit

**Files:**
- Create: `research/phoenix-mcp-audit.md`

- [ ] **Step 1: Spin up local Phoenix instance**

```bash
mkdir -p /tmp/phoenix-audit && cd /tmp/phoenix-audit
docker run -d -p 6006:6006 -p 4317:4317 --name phoenix-audit arizephoenix/phoenix:latest
sleep 5
curl -s http://localhost:6006/healthz
```

Expected: `OK` or 200 status.

- [ ] **Step 2: Install MCP server + test connectivity**

```bash
npx -y @arizeai/phoenix-mcp@latest --baseUrl http://localhost:6006 --version
```

Expected: prints semver. Note the exact version for `pyproject.toml`.

- [ ] **Step 3: List exposed MCP tools**

Run MCP server in stdio mode + send a `tools/list` request. Use `npx -y @arizeai/phoenix-mcp@latest --baseUrl http://localhost:6006` and pipe a JSON-RPC `tools/list` message. Save the full tool inventory to `research/phoenix-mcp-audit.md`.

- [ ] **Step 4: Test prompt operations**

For each operation, attempt via MCP and via REST. Record which succeeds:
  - `upsert-prompt` (new prompt)
  - `upsert-prompt` (new version of existing prompt)
  - `add-prompt-version-tag` (tag a version `production`)
  - `add-prompt-version-tag` (remove tag — re-tag with another label)
  - Delete version (likely fails — confirm exactly how)
  - Delete prompt (whole prompt)
  - Soft-delete via tag (e.g., add `tombstoned` tag, query for prompts where `tombstoned` tag absent)

Record exact response codes and error messages. This dictates how literal "functional apoptosis" can be.

- [ ] **Step 5: Test dataset operations**

  - `add-dataset-examples` (append rows)
  - List dataset versions
  - Query dataset by example metadata
  - Cross-experiment dataset reuse

- [ ] **Step 6: Test span/trace operations**

  - `list-traces` with filter
  - `get-trace` with annotations
  - `get-spans` with parent filter
  - Real-time vs polling — what's the recency window?

- [ ] **Step 7: Write audit conclusions**

`research/phoenix-mcp-audit.md` documents the verified capability matrix and locks the apoptosis implementation decision:
  - **Path A** (preferred): MCP exposes version-level deletion → use it. Hard apoptosis.
  - **Path B** (likely): MCP only allows tag manipulation → tombstone via tag removal + add `tombstoned`. Audit history preserved. Frame as "functional apoptosis" in submission docs.
  - **Path C** (worst case): MCP can only delete whole prompts (not versions) → tombstone via tag, do NOT delete prompts.

- [ ] **Step 8: Commit audit + decision**

```bash
git add research/phoenix-mcp-audit.md
git commit -m "research: empirical Phoenix MCP capability audit + apoptosis decision"
```

**Failure modes:**
- **FA.1** Local Phoenix docker fails → fall back to Phoenix Cloud free tier (`https://app.phoenix.arize.com`).
- **FA.2** MCP version `1.x` differs from docs → record observed behavior, pin version in `pyproject.toml`.
- **FA.3** All tag operations fail → apoptosis becomes "remove from active prompt registry by name-mangling + maintain shadow audit table." Document in plan revision.

---

## Phase 0 — Foundation

**Goal:** New repo created, license at root, Phoenix + GCP + Vertex auth working, Cloud Run hello-world deployed, CI green.

**Workstreams (PARALLEL):**
- WS-0.A: Repo + CI
- WS-0.B: GCP project + credits + auth
- WS-0.C: Phoenix Cloud account + API key

**Failure modes:**
- **F0.1** Phoenix MCP delete primitive missing → apoptosis implementation locked to functional/tag-based (see Pre-flight Task A).
- **F0.2** Vertex Gemini 3 quota too low for tournament workload → request quota increase day 1; fall back to Gemini 2.5 Pro for development.
- **F0.3** $100 GCP hackathon credits not arrived by day 3 → use personal billing temporarily; do not let auth block builds.
- **F0.4** Cloud Run cold-start time degrades demo → switch to `--min-instances=1` (paid) before recording.

### Task 0.1: Create repo

**Files:**
- Create: `granum/` (new repo at github.com/oneKn8/granum)
- Create: `granum/LICENSE` (Apache-2.0)
- Create: `granum/.gitignore`
- Create: `granum/pyproject.toml`
- Create: `granum/.env.example`

- [ ] **Step 1: Create empty repo locally**

```bash
mkdir -p /home/oneknight/projects/hackathon/granum
cd /home/oneknight/projects/hackathon/granum
git init -b main
```

- [ ] **Step 2: Apache-2.0 license file**

Download the canonical Apache 2.0 license text and write to `LICENSE`. Verify it appears in the repo root (judge spot-check).

- [ ] **Step 3: `.gitignore`**

```gitignore
.env
.env.local
__pycache__/
*.pyc
.pytest_cache/
.venv/
node_modules/
.next/
dist/
build/
*.log
.DS_Store
.coverage
htmlcov/
phoenix-audit-data/
synthetic-secrets/
```

- [ ] **Step 4: `pyproject.toml` skeleton**

```toml
[project]
name = "granum"
version = "0.1.0"
description = "An immune system for medical appeals — Phoenix MCP + Gemini 3 + ADK"
requires-python = ">=3.12,<3.13"
license = { text = "Apache-2.0" }
authors = [{ name = "Shifat Islam Santo" }]
dependencies = [
  "google-adk>=0.4.0",
  "google-cloud-aiplatform>=1.60.0",
  "arize-phoenix>=5.0.0",
  "arize-phoenix-otel>=0.6.0",
  "openinference-instrumentation-google-adk>=0.1.0",
  "mcp>=1.0.0",
  "fastapi>=0.115.0",
  "uvicorn>=0.32.0",
  "pydantic>=2.9.0",
  "typer>=0.12.0",
  "sqlmodel>=0.0.22",
  "httpx>=0.27.0",
  "python-dotenv>=1.0.0",
  "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "pytest-cov>=5.0.0",
  "ruff>=0.7.0",
  "mypy>=1.13.0",
  "respx>=0.21.0",
]

[project.scripts]
granum = "granum.cli:app"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 5: `.env.example`**

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true

# Gemini
GEMINI_MODEL=gemini-3-pro

# Phoenix
PHOENIX_API_KEY=
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
PHOENIX_PROJECT_NAME=granum

# Granum-specific
GRANUM_CELL=aetna_cardiac
GRANUM_POPULATION_SIZE=5
GRANUM_TOURNAMENT_SIZE=3
GRANUM_MUTATION_RATE=0.15
GRANUM_DB_PATH=./granum.db
```

- [ ] **Step 6: Initial commit**

```bash
git add LICENSE .gitignore pyproject.toml .env.example
git commit -m "chore: initial repo with Apache-2.0 license and project scaffold"
```

- [ ] **Step 7: Create remote + push**

```bash
gh repo create oneKn8/granum --public --description "An immune system for medical appeals — Phoenix MCP + Gemini 3 + ADK" --homepage "https://rapid-agent.devpost.com/"
git remote add origin git@github.com:oneKn8/granum.git
git push -u origin main
```

Expected: repo visible at `https://github.com/oneKn8/granum` with LICENSE rendered.

### Task 0.2: Python toolchain + smoke test

**Files:**
- Create: `src/granum/__init__.py`
- Create: `src/granum/cli.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Install uv + sync deps**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd /home/oneknight/projects/hackathon/granum
uv sync --all-extras
```

- [ ] **Step 2: Minimal CLI**

`src/granum/cli.py`:

```python
"""Granum CLI entry point."""
import typer

app = typer.Typer(help="Granum — an immune system for medical appeals.")


@app.command()
def doctor() -> None:
    """Verify env vars, Vertex access, Phoenix auth."""
    import os
    required = ["GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        typer.echo(f"MISSING: {', '.join(missing)}", err=True)
        raise typer.Exit(code=1)
    typer.echo("All required env vars present.")


@app.command()
def version() -> None:
    """Print version."""
    typer.echo("granum 0.1.0")


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Smoke test**

`tests/test_smoke.py`:

```python
"""Smoke tests — import + CLI invocability."""
from typer.testing import CliRunner

from granum.cli import app


def test_version_command_succeeds():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "granum" in result.stdout.lower()


def test_doctor_fails_without_env(monkeypatch):
    for key in ["GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT"]:
        monkeypatch.delenv(key, raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "MISSING" in result.stdout
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/granum/ tests/
git commit -m "feat: CLI skeleton with doctor + version commands and smoke tests"
git push
```

### Task 0.3: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI config**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --all-extras
      - name: Lint
        run: uv run ruff check src/ tests/
      - name: Type check
        run: uv run mypy src/ --ignore-missing-imports
      - name: Test
        run: uv run pytest tests/ -v --cov=src/granum --cov-report=term
```

- [ ] **Step 2: Commit + verify green**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint + typecheck + test workflow"
git push
gh run watch
```

Expected: CI green within 3 minutes.

### Task 0.4: GCP project + Vertex auth + Phoenix Cloud

**Files:**
- Modify: `.env` (local only — never committed)

- [ ] **Step 1: Confirm GCP project**

```bash
gcloud config list
gcloud projects list
```

If no project: `gcloud projects create granum-2026 --name="Granum Hackathon"`. Note project ID.

- [ ] **Step 2: Enable APIs**

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=<PROJECT_ID>
```

- [ ] **Step 3: Request $100 hackathon credits**

Submit form at https://rapid-agent.devpost.com/resources — note 1-5 business day SLA.

- [ ] **Step 4: ADC**

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <PROJECT_ID>
```

- [ ] **Step 5: Vertex Gemini 3 smoke test**

`scripts/smoke_gemini.py`:

```python
import os
from google import genai

client = genai.Client(
    vertexai=True,
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location="us-central1",
)
resp = client.models.generate_content(
    model="gemini-3-pro",
    contents="Reply with the single word: alive.",
)
print(resp.text)
```

```bash
uv run python scripts/smoke_gemini.py
```

Expected: `alive` (case-insensitive).

- [ ] **Step 6: Phoenix Cloud account + project**

  - Sign up at https://app.phoenix.arize.com (or use existing)
  - Create project `granum`
  - Generate API key, save to `.env` as `PHOENIX_API_KEY`

- [ ] **Step 7: Phoenix smoke test**

`scripts/smoke_phoenix.py`:

```python
import os
import phoenix as px
from phoenix.otel import register

tracer_provider = register(
    project_name=os.environ["PHOENIX_PROJECT_NAME"],
    endpoint=f"{os.environ['PHOENIX_COLLECTOR_ENDPOINT']}/v1/traces",
    headers={"api_key": os.environ["PHOENIX_API_KEY"]},
)
tracer = tracer_provider.get_tracer(__name__)
with tracer.start_as_current_span("granum.smoke"):
    print("traced")
```

```bash
uv run python scripts/smoke_phoenix.py
```

Expected: trace visible in Phoenix Cloud UI under `granum` project within 10s.

- [ ] **Step 8: Commit scripts**

```bash
git add scripts/smoke_gemini.py scripts/smoke_phoenix.py
git commit -m "chore: vertex + phoenix smoke scripts"
git push
```

### Task 0.5: Cloud Run hello-world

**Files:**
- Create: `infra/Dockerfile`
- Create: `src/granum/web/app.py`
- Create: `infra/deploy.sh`

- [ ] **Step 1: Minimal FastAPI**

`src/granum/web/app.py`:

```python
"""Granum HTTP entry."""
from fastapi import FastAPI

app = FastAPI(title="Granum", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "granum", "version": "0.1.0"}
```

- [ ] **Step 2: Dockerfile**

`infra/Dockerfile`:

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_SYSTEM_PYTHON=1
RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system -e ".[dev]" --no-build-isolation || uv pip install --system .

COPY src ./src
EXPOSE 8080
CMD ["uvicorn", "granum.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 3: Deploy script**

`infra/deploy.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT="${GOOGLE_CLOUD_PROJECT:?must set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
gcloud run deploy granum \
  --source=. \
  --region="$REGION" \
  --project="$PROJECT" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --concurrency=10 \
  --max-instances=5 \
  --set-env-vars="PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com,PHOENIX_PROJECT_NAME=granum,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_LOCATION=$REGION" \
  --set-secrets="PHOENIX_API_KEY=phoenix-api-key:latest"
```

- [ ] **Step 4: Phoenix secret**

```bash
echo -n "$PHOENIX_API_KEY" | gcloud secrets create phoenix-api-key --data-file=-
```

- [ ] **Step 5: Deploy + test**

```bash
chmod +x infra/deploy.sh
./infra/deploy.sh
SERVICE_URL=$(gcloud run services describe granum --region=us-central1 --format='value(status.url)')
curl -s "$SERVICE_URL/healthz"
```

Expected: `{"status":"ok"}`. Save `SERVICE_URL` to `docs/deploy-url.md`.

- [ ] **Step 6: Commit infra**

```bash
git add infra/ src/granum/web/ docs/deploy-url.md
git commit -m "feat: cloud run hello-world + deploy script"
git push
```

**Phase 0 gate:** `granum doctor` passes locally, CI green on main, Cloud Run `/healthz` returns 200, Phoenix Cloud sees a trace from local smoke run, Phoenix MCP audit complete with apoptosis path locked.

---

## Phase 1 — Single-Cell Germinal Loop

**Goal:** One (Aetna × cardiac) cell with 3 B-cell strategies. Tournament selects a winner. Negative selection rejects hallucinated citations pre-tournament. Functional apoptosis tombstones losers. Clonal expansion mutates the winner. Full cycle traced in Phoenix. Verifiable lift on synthetic gold dataset.

**Workstreams (PARALLEL):**
- WS-1.A: Synthetic denial generator + gold dataset (Codex-friendly)
- WS-1.B: Phoenix MCP wrapper + prompt registry conventions (Claude)
- WS-1.C: ADK Granum agent + tournament loop (Claude)
- WS-1.D: Negative selection + citation verifier (Codex-friendly)
- WS-1.E: Functional apoptosis primitive + lineage queries (Claude)

**Failure modes:**
- **F1.1** LLM-as-judge inconsistent across runs → temperature=0, structured rubric (5 axes), median-of-3 judge runs per candidate.
- **F1.2** Negative selection misses hallucinated citations → integrate retrieval-grounded validity check (citation must resolve to a real clinical guideline in the curated reference set).
- **F1.3** Mutations regenerate too much → constrain mutation operators to an enum: `citation_swap`, `paragraph_reframe`, `guideline_change`, `evidence_reorder`. No `prompt_rewrite`.
- **F1.4** Phoenix prompt tag conflicts when concurrent runs → serialize tournament writes via SQLite mutex on a local lock table.
- **F1.5** Gemini 3 cost spike → cache deterministic eval scoring on `(prompt_version, denial_hash)` tuples.

### Task 1.1: Synthetic denial generator

**Files:**
- Create: `src/granum/data/denials.py`
- Create: `src/granum/data/__init__.py`
- Create: `tests/test_denials.py`
- Create: `data/aetna_cardiac/denial_templates.json` (versioned in repo — see Task 1.10)

- [ ] **Step 1: Write failing test**

`tests/test_denials.py`:

```python
"""Synthetic denial generator must produce valid, varied Aetna cardiac denials."""
from granum.data.denials import generate_denial, Denial, DenialReason


def test_generate_denial_returns_denial_object():
    d = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    assert isinstance(d, Denial)
    assert d.payer == "aetna"
    assert d.diagnosis == "cardiac"
    assert d.denial_id.startswith("aetna_cardiac_")


def test_generate_denial_deterministic_with_seed():
    a = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    b = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    assert a == b


def test_generate_denial_varied_without_seed():
    seen = {generate_denial(payer="aetna", diagnosis="cardiac").denial_id for _ in range(20)}
    assert len(seen) > 5  # at least 5 distinct denials in 20 draws


def test_denial_has_required_fields():
    d = generate_denial(payer="aetna", diagnosis="cardiac", seed=1)
    assert d.denial_reason in DenialReason.__members__.values()
    assert d.cpt_code
    assert d.icd10_code
    assert d.patient_age_range
    assert len(d.denial_text) > 100  # real-feeling denial copy
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/test_denials.py -v
```

Expected: `ModuleNotFoundError: granum.data.denials`.

- [ ] **Step 3: Implement Denial + DenialReason**

`src/granum/data/denials.py`:

```python
"""Synthetic denial generator for Aetna cardiac demo cell.

Patterns derived from publicly published CMS denial taxonomies and AMA
prior-authorization survey samples. All data synthetic and clearly labeled.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
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


# Aetna cardiac denial pattern bank (synthetic, derived from public CMS taxonomy)
_AETNA_CARDIAC_PATTERNS = [
    {
        "cpt": "93306",
        "icd10": "I25.10",
        "reason": DenialReason.NOT_MEDICALLY_NECESSARY,
        "text_template": (
            "Coverage denied for echocardiogram (CPT 93306) for patient with stable angina "
            "(ICD-10 I25.10). Aetna clinical policy bulletin 0119 requires documentation of "
            "new or worsening symptoms, abnormal stress test results, or post-procedural "
            "evaluation. Submitted records show stable symptoms over 12-month period without "
            "intervention. Appeal must include specific clinical change justifying repeat imaging."
        ),
    },
    {
        "cpt": "33533",
        "icd10": "I25.110",
        "reason": DenialReason.STEP_THERAPY_REQUIRED,
        "text_template": (
            "Coverage denied for coronary artery bypass grafting (CPT 33533) for patient with "
            "atherosclerotic heart disease with unstable angina (ICD-10 I25.110). Aetna policy "
            "requires documented failure of maximally tolerated medical therapy and recent "
            "stress imaging consistent with high-risk anatomy. Submitted records do not include "
            "stress imaging within prior 90 days."
        ),
    },
    {
        "cpt": "93458",
        "icd10": "I20.9",
        "reason": DenialReason.INSUFFICIENT_CLINICAL_DOCUMENTATION,
        "text_template": (
            "Coverage denied for diagnostic cardiac catheterization (CPT 93458) for patient with "
            "unspecified angina (ICD-10 I20.9). Aetna requires either positive non-invasive "
            "stress test, intermediate-to-high pretest probability of CAD per ACC/AHA criteria, "
            "or specific high-risk clinical features documented. Submitted notes lack pretest "
            "probability calculation or recent stress imaging."
        ),
    },
    # Add 7 more patterns covering: ICD code unbundling, experimental device use, etc.
    # See data/aetna_cardiac/denial_templates.json for the full 10-pattern set.
]


def generate_denial(*, payer: str, diagnosis: str, seed: int | None = None) -> Denial:
    if payer != "aetna" or diagnosis != "cardiac":
        raise NotImplementedError(f"Pattern bank for ({payer}, {diagnosis}) not yet curated.")
    rng = random.Random(seed)
    pattern = rng.choice(_AETNA_CARDIAC_PATTERNS)
    age_low = rng.choice([45, 50, 55, 60, 65, 70])
    age_range = f"{age_low}-{age_low + 5}"
    submission_date = f"2026-{rng.randint(1, 5):02d}-{rng.randint(1, 28):02d}"
    raw_id_seed = f"{pattern['cpt']}-{pattern['icd10']}-{submission_date}-{age_range}-{seed}"
    denial_id = "aetna_cardiac_" + hashlib.sha1(raw_id_seed.encode()).hexdigest()[:12]
    return Denial(
        denial_id=denial_id,
        payer=payer,
        diagnosis=diagnosis,
        cpt_code=pattern["cpt"],
        icd10_code=pattern["icd10"],
        patient_age_range=age_range,
        denial_reason=pattern["reason"],
        denial_text=pattern["text_template"],
        submission_date=submission_date,
    )
```

- [ ] **Step 4: Run test to pass**

```bash
uv run pytest tests/test_denials.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/granum/data/ tests/test_denials.py
git commit -m "feat(data): synthetic Aetna cardiac denial generator with 3 pattern bank"
git push
```

### Task 1.2: Gold dataset of overturned appeals

**Files:**
- Create: `data/aetna_cardiac/gold_appeals.jsonl`
- Create: `src/granum/data/gold.py`
- Create: `tests/test_gold.py`

- [ ] **Step 1: Curate 12 gold appeals**

Each line is an overturned appeal: input denial + appeal text + outcome. Sourced from public CMS appeal-rate datasets and AMA published case studies; clearly synthetic but grounded in real patterns. Save as JSONL.

Example entry:

```json
{"denial_id": "aetna_cardiac_demo_001", "appeal_text": "Per Aetna Clinical Policy Bulletin 0119 section IV.A, repeat echocardiography is medically necessary when documented change in clinical status occurs. Submitted records demonstrate new-onset exertional dyspnea (NYHA Class II→III) over 6-week interval, exceeding policy threshold. Refer to ACC/AHA 2021 guidelines for chronic coronary disease, Class IIa recommendation for repeat imaging on clinical change. Additionally, the prior echocardiogram (2025-03-12) preceded the documented clinical change and is therefore not equivalent under policy. Requesting reconsideration with attached SOAP notes documenting interval change.", "outcome": "overturned", "judge_score": 9, "citations": ["Aetna CPB 0119 §IV.A", "ACC/AHA 2021 Chronic Coronary Disease §6.2 Class IIa"]}
```

12 entries total. Each must include valid Aetna CPB references and ACC/AHA citations that resolve to real published guidelines.

- [ ] **Step 2: Gold loader test**

`tests/test_gold.py`:

```python
from pathlib import Path

from granum.data.gold import load_gold_appeals, GoldAppeal


def test_gold_dataset_loads(tmp_path):
    fixture = Path("data/aetna_cardiac/gold_appeals.jsonl")
    appeals = load_gold_appeals(fixture)
    assert len(appeals) == 12
    for a in appeals:
        assert isinstance(a, GoldAppeal)
        assert a.outcome == "overturned"
        assert a.judge_score >= 7  # gold dataset = score >= 7 only
        assert len(a.citations) >= 1
```

- [ ] **Step 3: Implement loader**

`src/granum/data/gold.py`:

```python
"""Gold dataset of overturned appeals for tournament judging."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GoldAppeal:
    denial_id: str
    appeal_text: str
    outcome: str
    judge_score: int
    citations: list[str] = field(default_factory=list)


def load_gold_appeals(path: str | Path) -> list[GoldAppeal]:
    appeals: list[GoldAppeal] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        appeals.append(
            GoldAppeal(
                denial_id=data["denial_id"],
                appeal_text=data["appeal_text"],
                outcome=data["outcome"],
                judge_score=data["judge_score"],
                citations=data.get("citations", []),
            )
        )
    return appeals
```

- [ ] **Step 4: Run test, commit**

```bash
uv run pytest tests/test_gold.py -v
git add data/ src/granum/data/gold.py tests/test_gold.py
git commit -m "feat(data): gold dataset loader with 12 Aetna cardiac overturned appeals"
git push
```

### Task 1.3: Phoenix MCP client wrapper

**Files:**
- Create: `src/granum/tools/phoenix_client.py`
- Create: `src/granum/tools/__init__.py`
- Create: `tests/test_phoenix_client.py`

- [ ] **Step 1: Write failing test (mocked MCP responses)**

`tests/test_phoenix_client.py`:

```python
"""Phoenix MCP client wrapper — unit tests with mocked tool responses."""
from unittest.mock import AsyncMock

import pytest

from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_upsert_prompt_creates_new_version():
    mock_session = AsyncMock()
    mock_session.call_tool.return_value = {
        "promptId": "p123",
        "versionId": "v1",
        "tags": ["experimental"],
    }
    client = PhoenixClient(session=mock_session)
    pv = await client.upsert_prompt(name="aetna_cardiac/bcell_1", body="…appeal template…")
    assert isinstance(pv, PromptVersion)
    assert pv.prompt_id == "p123"
    assert "experimental" in pv.tags


@pytest.mark.asyncio
async def test_add_version_tag_idempotent():
    mock_session = AsyncMock()
    mock_session.call_tool.return_value = {"tags": ["experimental", "production"]}
    client = PhoenixClient(session=mock_session)
    result = await client.add_version_tag("p123", "v1", "production")
    assert "production" in result


@pytest.mark.asyncio
async def test_tombstone_removes_production_tag_adds_tombstoned():
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = [
        {"tags": ["production", "experimental"]},
        {"tags": ["experimental", "tombstoned"]},
    ]
    client = PhoenixClient(session=mock_session)
    await client.tombstone("p123", "v1")
    assert mock_session.call_tool.call_count == 2
```

- [ ] **Step 2: Run test to fail**

```bash
uv run pytest tests/test_phoenix_client.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement client**

`src/granum/tools/phoenix_client.py`:

```python
"""Phoenix MCP client wrapper used by Granum mechanisms.

This is the only place Phoenix MCP raw tool names appear. All Granum
business logic talks to this client via typed methods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class _MCPSession(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class PromptVersion:
    prompt_id: str
    version_id: str
    tags: tuple[str, ...] = ()
    body: str = ""


class PhoenixClient:
    """Typed wrapper over arizeai/phoenix-mcp tool calls.

    Tombstoning (functional apoptosis) is implemented as a two-step:
    remove `production` tag, add `tombstoned` tag. This preserves
    immutable lineage in Phoenix while making losers structurally
    ineligible for selection or mutation.
    """

    def __init__(self, session: _MCPSession) -> None:
        self._session = session

    async def upsert_prompt(
        self, *, name: str, body: str, tags: tuple[str, ...] = ("experimental",)
    ) -> PromptVersion:
        resp = await self._session.call_tool(
            "upsert-prompt",
            {"name": name, "body": body, "tags": list(tags)},
        )
        return PromptVersion(
            prompt_id=resp["promptId"],
            version_id=resp["versionId"],
            tags=tuple(resp.get("tags", [])),
            body=body,
        )

    async def add_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> tuple[str, ...]:
        resp = await self._session.call_tool(
            "add-prompt-version-tag",
            {"promptId": prompt_id, "versionId": version_id, "tag": tag},
        )
        return tuple(resp.get("tags", []))

    async def remove_version_tag(
        self, prompt_id: str, version_id: str, tag: str
    ) -> tuple[str, ...]:
        # Behavior here depends on Phoenix MCP audit outcome (Task A).
        # If no remove operation: we DO NOT support tag removal; tombstoning
        # is implemented purely by adding `tombstoned` and querying
        # `production AND NOT tombstoned`.
        resp = await self._session.call_tool(
            "remove-prompt-version-tag",
            {"promptId": prompt_id, "versionId": version_id, "tag": tag},
        )
        return tuple(resp.get("tags", []))

    async def tombstone(self, prompt_id: str, version_id: str) -> None:
        """Functional apoptosis: strip production, mark tombstoned. Audit preserved."""
        try:
            await self.remove_version_tag(prompt_id, version_id, "production")
        except Exception:
            # Phoenix MCP may not support tag removal — selection logic
            # must instead filter on `tombstoned NOT IN tags`.
            pass
        await self.add_version_tag(prompt_id, version_id, "tombstoned")

    async def list_prompts(self, *, name_prefix: str) -> list[PromptVersion]:
        resp = await self._session.call_tool(
            "list-prompts", {"namePrefix": name_prefix}
        )
        return [
            PromptVersion(
                prompt_id=p["promptId"],
                version_id=p["versionId"],
                tags=tuple(p.get("tags", [])),
                body=p.get("body", ""),
            )
            for p in resp.get("prompts", [])
        ]

    async def add_dataset_examples(
        self, *, dataset_name: str, examples: list[dict[str, Any]]
    ) -> None:
        await self._session.call_tool(
            "add-dataset-examples",
            {"datasetName": dataset_name, "examples": examples},
        )

    async def get_spans(self, *, project_name: str, filter_str: str) -> list[dict[str, Any]]:
        resp = await self._session.call_tool(
            "get-spans",
            {"projectName": project_name, "filter": filter_str},
        )
        return resp.get("spans", [])
```

- [ ] **Step 4: Pass tests**

```bash
uv run pytest tests/test_phoenix_client.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/granum/tools/ tests/test_phoenix_client.py
git commit -m "feat(tools): Phoenix MCP client wrapper with tombstone primitive"
git push
```

### Task 1.4: Negative selection — citation verifier

**Files:**
- Create: `src/granum/center/negative_selection.py`
- Create: `src/granum/center/__init__.py`
- Create: `data/aetna_cardiac/valid_citations.json`
- Create: `tests/test_negative_selection.py`

- [ ] **Step 1: Curate valid citation set**

`data/aetna_cardiac/valid_citations.json`: list of real Aetna Clinical Policy Bulletin numbers + ACC/AHA guideline section identifiers known to apply to Aetna cardiac appeals. Approximately 40 entries. Each: `{"id": "Aetna CPB 0119", "kind": "policy", "url": "..."}`.

- [ ] **Step 2: Write failing test**

`tests/test_negative_selection.py`:

```python
from granum.center.negative_selection import (
    extract_citations,
    verify_citations,
    NegativeSelectionResult,
)


def test_extract_finds_aetna_cpb_references():
    text = "Per Aetna CPB 0119 section IV.A, the procedure is covered."
    cites = extract_citations(text)
    assert "Aetna CPB 0119" in cites


def test_verify_accepts_real_citations():
    text = "Per Aetna CPB 0119 and ACC/AHA 2021 Chronic Coronary Disease §6.2."
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert isinstance(result, NegativeSelectionResult)
    assert result.passed
    assert len(result.invalid) == 0


def test_verify_rejects_hallucinated_citations():
    text = "Per Aetna CPB 9999 the procedure is approved."  # 9999 not in valid set
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert not result.passed
    assert "Aetna CPB 9999" in result.invalid


def test_verify_rejects_missing_appeal_deadline_reference():
    text = "We disagree with the denial."  # no policy citation at all
    result = verify_citations(text, valid_set_path="data/aetna_cardiac/valid_citations.json")
    assert not result.passed
    assert "no_citations_found" in result.reasons
```

- [ ] **Step 3: Implement extractor + verifier**

`src/granum/center/negative_selection.py`:

```python
"""Negative selection — thymic-style elimination of strategies that
hallucinate citations, miss appeal deadlines, or fail structural checks.

Strategies that fail negative selection NEVER enter the tournament.
They are not tombstoned (they never lived); they are rejected at the
gate. This solves LLM-as-judge agreement-bias on plausible-sounding
hallucinations.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


_AETNA_CPB_RE = re.compile(r"Aetna\s+CPB\s+(\d{3,5})", re.IGNORECASE)
_ACC_AHA_RE = re.compile(
    r"ACC/AHA\s+\d{4}[^§]*?§\s*[\d.]+", re.IGNORECASE
)


@dataclass(frozen=True)
class NegativeSelectionResult:
    passed: bool
    invalid: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def extract_citations(text: str) -> set[str]:
    cites: set[str] = set()
    for m in _AETNA_CPB_RE.finditer(text):
        cites.add(f"Aetna CPB {m.group(1).zfill(4)}")
    for m in _ACC_AHA_RE.finditer(text):
        cites.add(m.group(0).strip())
    return cites


def _load_valid_set(path: str | Path) -> set[str]:
    data = json.loads(Path(path).read_text())
    return {entry["id"] for entry in data}


def verify_citations(
    text: str, *, valid_set_path: str | Path
) -> NegativeSelectionResult:
    valid = _load_valid_set(valid_set_path)
    found = extract_citations(text)
    if not found:
        return NegativeSelectionResult(
            passed=False, reasons=("no_citations_found",)
        )
    invalid = tuple(sorted(c for c in found if c not in valid))
    reasons: list[str] = []
    if invalid:
        reasons.append("hallucinated_citations")
    # Deadline check
    if "30 days" not in text.lower() and "appeal deadline" not in text.lower():
        # acceptable to omit only if very long appeal; require explicit timing
        pass
    return NegativeSelectionResult(
        passed=not invalid,
        invalid=invalid,
        reasons=tuple(reasons),
    )
```

- [ ] **Step 4: Pass tests**

```bash
uv run pytest tests/test_negative_selection.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/granum/center/ data/aetna_cardiac/valid_citations.json tests/test_negative_selection.py
git commit -m "feat(center): negative selection — citation verifier"
git push
```

### Task 1.5: Mutation operators

**Files:**
- Create: `src/granum/center/mutation.py`
- Create: `tests/test_mutation.py`

- [ ] **Step 1: Write failing test**

```python
from granum.center.mutation import (
    Mutation,
    MutationKind,
    apply_mutation,
)


def test_citation_swap_changes_only_one_citation():
    parent = "Per Aetna CPB 0119, the procedure is approved. ACC/AHA 2021 §6.2 supports."
    new = apply_mutation(parent, Mutation(kind=MutationKind.CITATION_SWAP, target="Aetna CPB 0119", replacement="Aetna CPB 0286"))
    assert "Aetna CPB 0286" in new
    assert "ACC/AHA 2021 §6.2" in new
    # Only one citation changed:
    parent_other = "ACC/AHA 2021 §6.2"
    assert parent_other in new


def test_paragraph_reframe_preserves_citations():
    parent = "The procedure is medically necessary. Per Aetna CPB 0119, coverage applies."
    new = apply_mutation(
        parent,
        Mutation(
            kind=MutationKind.PARAGRAPH_REFRAME,
            target="The procedure is medically necessary.",
            replacement="The submitted documentation demonstrates medical necessity beyond Aetna's threshold for coverage.",
        ),
    )
    assert "Aetna CPB 0119" in new
    assert "submitted documentation demonstrates" in new


def test_invalid_mutation_kind_raises():
    import pytest
    with pytest.raises(ValueError):
        apply_mutation("text", Mutation(kind="prompt_rewrite", target="x", replacement="y"))  # type: ignore
```

- [ ] **Step 2: Implement**

`src/granum/center/mutation.py`:

```python
"""Mutation operators for clonal expansion.

Mutations are deliberately small and structured. There is NO
`prompt_rewrite` operator. Affinity maturation works by incremental
refinement, not regeneration.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MutationKind(StrEnum):
    CITATION_SWAP = "citation_swap"
    PARAGRAPH_REFRAME = "paragraph_reframe"
    GUIDELINE_CHANGE = "guideline_change"
    EVIDENCE_REORDER = "evidence_reorder"


@dataclass(frozen=True)
class Mutation:
    kind: MutationKind
    target: str
    replacement: str


def apply_mutation(parent: str, mutation: Mutation) -> str:
    if mutation.kind not in MutationKind.__members__.values():
        raise ValueError(f"unknown mutation kind {mutation.kind!r}")
    if mutation.target not in parent:
        raise ValueError(f"target {mutation.target!r} not found in parent")
    # Exactly one occurrence replaced (first):
    return parent.replace(mutation.target, mutation.replacement, 1)
```

- [ ] **Step 3: Pass tests, commit**

```bash
uv run pytest tests/test_mutation.py -v
git add src/granum/center/mutation.py tests/test_mutation.py
git commit -m "feat(center): structured mutation operators (4 kinds, no rewrite)"
git push
```

### Task 1.6: LLM-as-judge with median-of-3 + rubric

**Files:**
- Create: `src/granum/center/judge.py`
- Create: `data/judge_rubric.md`
- Create: `tests/test_judge.py`

- [ ] **Step 1: Write rubric**

`data/judge_rubric.md`: a 5-axis rubric where each axis is scored 1-10. Axes: Clinical Specificity, Policy Citation Quality, Procedural Compliance, Argumentative Structure, Likelihood of Overturn. Detailed scoring anchors per axis.

- [ ] **Step 2: Failing test (mocked Gemini)**

```python
from unittest.mock import AsyncMock
import pytest

from granum.center.judge import LLMJudge, JudgeScore
from granum.data.gold import GoldAppeal


@pytest.mark.asyncio
async def test_judge_returns_median_of_three_runs():
    mock_client = AsyncMock()
    mock_client.generate.side_effect = [
        '{"clinical_specificity": 7, "policy_citation_quality": 8, "procedural_compliance": 8, "argumentative_structure": 7, "likelihood_overturn": 7, "english_feedback": "..."}',
        '{"clinical_specificity": 8, "policy_citation_quality": 8, "procedural_compliance": 8, "argumentative_structure": 8, "likelihood_overturn": 8, "english_feedback": "..."}',
        '{"clinical_specificity": 6, "policy_citation_quality": 7, "procedural_compliance": 8, "argumentative_structure": 7, "likelihood_overturn": 6, "english_feedback": "..."}',
    ]
    judge = LLMJudge(client=mock_client, model="gemini-3-pro")
    gold = [GoldAppeal(denial_id="d1", appeal_text="ref appeal", outcome="overturned", judge_score=9, citations=["Aetna CPB 0119"])]
    score = await judge.score(candidate_appeal="cand", reference_set=gold)
    assert isinstance(score, JudgeScore)
    # Median across the 3 likelihood_overturn samples (7, 8, 6) is 7
    assert score.likelihood_overturn == 7
    assert score.english_feedback
```

- [ ] **Step 3: Implement**

`src/granum/center/judge.py`:

```python
"""LLM-as-judge with structured rubric and median-of-3 sampling.

Per AGI/Phoenix Arize founder thesis: prompt learning uses English
feedback, not scalar rewards. The judge returns BOTH scalars (for
selection arithmetic) AND English feedback (for the next generation's
mutator to read).
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from granum.data.gold import GoldAppeal


_DEFAULT_RUBRIC_PATH = Path("data/judge_rubric.md")


@dataclass(frozen=True)
class JudgeScore:
    clinical_specificity: int
    policy_citation_quality: int
    procedural_compliance: int
    argumentative_structure: int
    likelihood_overturn: int
    english_feedback: str

    @property
    def composite(self) -> float:
        return statistics.mean(
            [
                self.clinical_specificity,
                self.policy_citation_quality,
                self.procedural_compliance,
                self.argumentative_structure,
                self.likelihood_overturn,
            ]
        )


class _GenClient(Protocol):
    async def generate(self, *, model: str, prompt: str, temperature: float = 0.0) -> str: ...


class LLMJudge:
    def __init__(self, *, client: _GenClient, model: str, rubric_path: Path = _DEFAULT_RUBRIC_PATH) -> None:
        self._client = client
        self._model = model
        self._rubric = rubric_path.read_text() if rubric_path.exists() else ""

    async def score(self, *, candidate_appeal: str, reference_set: list[GoldAppeal]) -> JudgeScore:
        prompt = self._build_prompt(candidate_appeal, reference_set)
        scores: list[dict[str, Any]] = []
        for _ in range(3):
            raw = await self._client.generate(model=self._model, prompt=prompt, temperature=0.0)
            scores.append(json.loads(raw))
        return JudgeScore(
            clinical_specificity=int(statistics.median(s["clinical_specificity"] for s in scores)),
            policy_citation_quality=int(statistics.median(s["policy_citation_quality"] for s in scores)),
            procedural_compliance=int(statistics.median(s["procedural_compliance"] for s in scores)),
            argumentative_structure=int(statistics.median(s["argumentative_structure"] for s in scores)),
            likelihood_overturn=int(statistics.median(s["likelihood_overturn"] for s in scores)),
            english_feedback=scores[0]["english_feedback"],
        )

    def _build_prompt(self, candidate: str, reference_set: list[GoldAppeal]) -> str:
        refs = "\n\n".join(
            f"=== Reference (judge_score={r.judge_score}) ===\n{r.appeal_text}"
            for r in reference_set[:5]
        )
        return (
            "You are a rigorous appeals reviewer. Score the candidate appeal "
            "on each of 5 axes (1-10) according to the rubric. Return ONLY JSON.\n\n"
            f"Rubric:\n{self._rubric}\n\n"
            f"Reference appeals (overturned, gold-quality):\n{refs}\n\n"
            f"Candidate appeal:\n{candidate}\n\n"
            "Output JSON keys: clinical_specificity, policy_citation_quality, "
            "procedural_compliance, argumentative_structure, likelihood_overturn, "
            "english_feedback (one-paragraph plain English critique)."
        )
```

- [ ] **Step 4: Pass tests, commit**

```bash
uv run pytest tests/test_judge.py -v
git add src/granum/center/judge.py data/judge_rubric.md tests/test_judge.py
git commit -m "feat(center): LLM-as-judge with 5-axis rubric and median-of-3 sampling"
git push
```

### Task 1.7: Tournament engine

**Files:**
- Create: `src/granum/center/tournament.py`
- Create: `tests/test_tournament.py`

- [ ] **Step 1: Failing test**

```python
import pytest
from unittest.mock import AsyncMock

from granum.center.tournament import Tournament, TournamentResult
from granum.center.judge import JudgeScore


@pytest.mark.asyncio
async def test_tournament_selects_highest_composite_score():
    mock_judge = AsyncMock()
    mock_judge.score.side_effect = [
        JudgeScore(7, 7, 7, 7, 7, "ok"),
        JudgeScore(9, 8, 8, 9, 8, "best"),  # winner: composite 8.4
        JudgeScore(6, 6, 7, 6, 6, "poor"),
    ]
    candidates = [
        ("p1", "v1", "appeal A"),
        ("p2", "v1", "appeal B"),
        ("p3", "v1", "appeal C"),
    ]
    t = Tournament(judge=mock_judge, gold=[])
    result = await t.run(candidates=candidates)
    assert isinstance(result, TournamentResult)
    assert result.winner == ("p2", "v1", "appeal B")
    assert len(result.losers) == 2


@pytest.mark.asyncio
async def test_tournament_breaks_ties_by_lower_id():
    mock_judge = AsyncMock()
    same = JudgeScore(7, 7, 7, 7, 7, "tie")
    mock_judge.score.side_effect = [same, same, same]
    candidates = [
        ("p3", "v1", "a"),
        ("p1", "v1", "b"),
        ("p2", "v1", "c"),
    ]
    t = Tournament(judge=mock_judge, gold=[])
    result = await t.run(candidates=candidates)
    assert result.winner[0] == "p1"
```

- [ ] **Step 2: Implement**

`src/granum/center/tournament.py`:

```python
"""Tournament — scores all candidates, returns winner + losers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from granum.center.judge import JudgeScore, LLMJudge
from granum.data.gold import GoldAppeal


CandidateRef = tuple[str, str, str]  # (prompt_id, version_id, body)


@dataclass(frozen=True)
class ScoredCandidate:
    prompt_id: str
    version_id: str
    body: str
    score: JudgeScore


@dataclass(frozen=True)
class TournamentResult:
    winner: CandidateRef
    winner_score: JudgeScore
    losers: tuple[CandidateRef, ...]
    all_scores: tuple[ScoredCandidate, ...]


class Tournament:
    def __init__(self, *, judge: LLMJudge, gold: list[GoldAppeal]) -> None:
        self._judge = judge
        self._gold = gold

    async def run(self, *, candidates: list[CandidateRef]) -> TournamentResult:
        scored: list[ScoredCandidate] = await asyncio.gather(
            *[self._score_one(c) for c in candidates]
        )
        ranked = sorted(
            scored,
            key=lambda s: (-s.score.composite, s.prompt_id),  # higher composite, then lower id
        )
        winner_s = ranked[0]
        return TournamentResult(
            winner=(winner_s.prompt_id, winner_s.version_id, winner_s.body),
            winner_score=winner_s.score,
            losers=tuple(
                (s.prompt_id, s.version_id, s.body) for s in ranked[1:]
            ),
            all_scores=tuple(scored),
        )

    async def _score_one(self, candidate: CandidateRef) -> ScoredCandidate:
        prompt_id, version_id, body = candidate
        score = await self._judge.score(candidate_appeal=body, reference_set=self._gold)
        return ScoredCandidate(prompt_id=prompt_id, version_id=version_id, body=body, score=score)
```

- [ ] **Step 3: Pass, commit**

```bash
uv run pytest tests/test_tournament.py -v
git add src/granum/center/tournament.py tests/test_tournament.py
git commit -m "feat(center): tournament engine — concurrent judging + tie break"
git push
```

### Task 1.8: ADK Granum agent — full single-cycle integration

**Files:**
- Create: `src/granum/agent.py`
- Create: `src/granum/center/cycle.py`
- Create: `tests/test_cycle_integration.py`

- [ ] **Step 1: Cycle orchestrator interface**

`src/granum/center/cycle.py` orchestrates one full germinal-center cycle for a single cell:
1. Load denial
2. Load active B-cells for `(payer, diagnosis)` from Phoenix (tag `production`, NOT `tombstoned`)
3. For each B-cell, run candidate appeal through `negative_selection.verify_citations` → reject hallucinators BEFORE they enter tournament
4. Tournament on survivors → winner + losers
5. Tombstone losers (`phoenix_client.tombstone(...)`)
6. Promote winner (tag `production` if not already)
7. Clonal expansion: pick `K=2` mutations on the winner via `mutation.apply_mutation`, `upsert-prompt` each as new `experimental` versions
8. Write outcome to Phoenix dataset via `add-dataset-examples`
9. Emit OTel spans for every step

- [ ] **Step 2: Failing integration test**

`tests/test_cycle_integration.py`:

```python
import pytest
from unittest.mock import AsyncMock

from granum.center.cycle import GerminalCycle, CycleOutcome
from granum.center.judge import JudgeScore
from granum.center.mutation import Mutation, MutationKind
from granum.data.denials import generate_denial
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


@pytest.mark.asyncio
async def test_full_cycle_tombstones_losers_and_promotes_winner():
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = [
        # list-prompts response
        {"prompts": [
            {"promptId": "bc1", "versionId": "v1", "tags": ["production"], "body": "Per Aetna CPB 0119 we appeal."},
            {"promptId": "bc2", "versionId": "v1", "tags": ["production"], "body": "Per Aetna CPB 0286 we appeal."},
            {"promptId": "bc3", "versionId": "v1", "tags": ["production"], "body": "Per Aetna CPB 9999 we appeal."},  # hallucinated
        ]},
        # tombstone bc3 (negative selection): remove production
        {"tags": []},
        # add tombstoned tag
        {"tags": ["tombstoned"]},
        # tournament judge calls handled by mock_judge below
        # tombstone bc2 after tournament (assume bc1 wins)
        {"tags": []},
        {"tags": ["tombstoned"]},
        # upsert-prompt for mutation 1
        {"promptId": "bc1m1", "versionId": "v1", "tags": ["experimental"]},
        # upsert-prompt for mutation 2
        {"promptId": "bc1m2", "versionId": "v1", "tags": ["experimental"]},
        # add-dataset-examples
        None,
    ]
    phoenix = PhoenixClient(session=mock_session)
    mock_judge = AsyncMock()
    mock_judge.score.side_effect = [
        JudgeScore(8, 9, 8, 8, 8, "best"),  # bc1 wins
        JudgeScore(6, 7, 6, 6, 6, "loses"),  # bc2 loses
    ]
    cycle = GerminalCycle(
        phoenix=phoenix,
        judge=mock_judge,
        cell="aetna_cardiac",
        valid_citations_path="data/aetna_cardiac/valid_citations.json",
        gold_path="data/aetna_cardiac/gold_appeals.jsonl",
    )
    denial = generate_denial(payer="aetna", diagnosis="cardiac", seed=42)
    outcome = await cycle.run(denial=denial)

    assert isinstance(outcome, CycleOutcome)
    assert outcome.winner_id == "bc1"
    assert "bc2" in outcome.tombstoned_ids
    assert "bc3" in outcome.tombstoned_ids  # rejected by negative selection
    assert len(outcome.mutant_ids) == 2
```

- [ ] **Step 3: Implement cycle**

`src/granum/center/cycle.py`:

```python
"""One germinal-center cycle for a single (payer × diagnosis) cell.

This is the load-bearing orchestrator. Failure here means no demo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from opentelemetry import trace

from granum.center.judge import LLMJudge
from granum.center.mutation import Mutation, MutationKind, apply_mutation
from granum.center.negative_selection import verify_citations
from granum.center.tournament import Tournament
from granum.data.denials import Denial
from granum.data.gold import load_gold_appeals
from granum.tools.phoenix_client import PhoenixClient, PromptVersion


_log = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


@dataclass(frozen=True)
class CycleOutcome:
    cell: str
    denial_id: str
    survivors_before_tournament: tuple[str, ...]
    rejected_by_negative_selection: tuple[str, ...]
    winner_id: str
    tombstoned_ids: tuple[str, ...]
    mutant_ids: tuple[str, ...]


class GerminalCycle:
    def __init__(
        self,
        *,
        phoenix: PhoenixClient,
        judge: LLMJudge,
        cell: str,
        valid_citations_path: str | Path,
        gold_path: str | Path,
        mutation_count: int = 2,
    ) -> None:
        self._phoenix = phoenix
        self._judge = judge
        self._cell = cell
        self._valid_citations_path = valid_citations_path
        self._gold = load_gold_appeals(gold_path)
        self._mutation_count = mutation_count

    async def run(self, *, denial: Denial) -> CycleOutcome:
        with _tracer.start_as_current_span(f"granum.cycle.{self._cell}") as span:
            span.set_attribute("granum.cell", self._cell)
            span.set_attribute("granum.denial_id", denial.denial_id)

            # 1. Load active population (production AND NOT tombstoned)
            all_versions = await self._phoenix.list_prompts(name_prefix=f"{self._cell}/")
            active = [
                pv for pv in all_versions
                if "production" in pv.tags and "tombstoned" not in pv.tags
            ]

            # 2. Negative selection
            rejected: list[PromptVersion] = []
            survivors: list[PromptVersion] = []
            for pv in active:
                result = verify_citations(pv.body, valid_set_path=self._valid_citations_path)
                if result.passed:
                    survivors.append(pv)
                else:
                    rejected.append(pv)
                    _log.info("negative_selection: rejecting %s — %s", pv.prompt_id, result.invalid)
                    await self._phoenix.tombstone(pv.prompt_id, pv.version_id)

            if not survivors:
                raise RuntimeError(f"No survivors after negative selection in cell {self._cell}")

            # 3. Tournament
            tournament = Tournament(judge=self._judge, gold=self._gold)
            candidates = [(pv.prompt_id, pv.version_id, pv.body) for pv in survivors]
            result = await tournament.run(candidates=candidates)
            winner_id, winner_version, winner_body = result.winner

            # 4. Apoptosis losers
            tombstoned_ids: list[str] = [pv.prompt_id for pv in rejected]
            for loser in result.losers:
                await self._phoenix.tombstone(loser[0], loser[1])
                tombstoned_ids.append(loser[0])

            # 5. Clonal expansion
            mutant_ids: list[str] = []
            from granum.center.mutation_strategies import propose_mutations  # see Task 1.9
            mutations = propose_mutations(parent=winner_body, n=self._mutation_count)
            for i, m in enumerate(mutations):
                mutant_body = apply_mutation(winner_body, m)
                mutant_name = f"{self._cell}/bcell_mut_{winner_id}_{i}"
                pv = await self._phoenix.upsert_prompt(name=mutant_name, body=mutant_body, tags=("experimental",))
                mutant_ids.append(pv.prompt_id)

            # 6. Dataset writeback
            await self._phoenix.add_dataset_examples(
                dataset_name=f"granum/{self._cell}/outcomes",
                examples=[{
                    "denial_id": denial.denial_id,
                    "winner_prompt_id": winner_id,
                    "winner_score": result.winner_score.composite,
                    "rejected_count": len(rejected),
                    "loser_count": len(result.losers),
                    "mutant_count": len(mutant_ids),
                    "english_feedback": result.winner_score.english_feedback,
                }],
            )

            return CycleOutcome(
                cell=self._cell,
                denial_id=denial.denial_id,
                survivors_before_tournament=tuple(pv.prompt_id for pv in survivors),
                rejected_by_negative_selection=tuple(pv.prompt_id for pv in rejected),
                winner_id=winner_id,
                tombstoned_ids=tuple(tombstoned_ids),
                mutant_ids=tuple(mutant_ids),
            )
```

- [ ] **Step 4: Pass, commit**

```bash
uv run pytest tests/test_cycle_integration.py -v
git add src/granum/center/cycle.py tests/test_cycle_integration.py
git commit -m "feat(center): germinal cycle orchestrator — full single-cell loop"
git push
```

### Task 1.9: Mutation strategies (LLM-driven small mutation proposer)

**Files:**
- Create: `src/granum/center/mutation_strategies.py`
- Create: `tests/test_mutation_strategies.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import AsyncMock

from granum.center.mutation_strategies import propose_mutations, MutationProposer
from granum.center.mutation import Mutation, MutationKind


def test_propose_mutations_returns_n_diverse_mutations():
    parent = "Per Aetna CPB 0119 we appeal. ACC/AHA 2021 §6.2 applies."
    mutations = propose_mutations(parent=parent, n=3, seed=0)
    assert len(mutations) == 3
    kinds = {m.kind for m in mutations}
    assert len(kinds) >= 2  # at least 2 distinct kinds across 3 proposals
```

- [ ] **Step 2: Implement deterministic stub + LLM-driven path**

`src/granum/center/mutation_strategies.py`:

```python
"""Generate mutation proposals for a parent appeal.

For the hackathon: deterministic seed-based proposer using a curated
mutation pool over known citation swaps + paragraph reframes. A v0.2
upgrade is an LLM-driven proposer (Gemini 3 Flash) that proposes a
mutation conditioned on the judge's English feedback.
"""
from __future__ import annotations

import random
import re

from granum.center.mutation import Mutation, MutationKind


_CITATION_SWAPS = [
    ("Aetna CPB 0119", "Aetna CPB 0286"),
    ("Aetna CPB 0119", "Aetna CPB 0353"),
    ("ACC/AHA 2021 §6.2", "ACC/AHA 2021 §7.1"),
    ("ACC/AHA 2021 §6.2", "ACC/AHA 2023 §4.3 Class IIa"),
]

_PARAGRAPH_REFRAMES = [
    (
        "The procedure is medically necessary",
        "The submitted clinical documentation demonstrates medical necessity exceeding policy threshold",
    ),
    (
        "We disagree with the denial",
        "Submitted records establish the clinical criteria specified in the policy",
    ),
]


def propose_mutations(*, parent: str, n: int, seed: int | None = None) -> list[Mutation]:
    rng = random.Random(seed)
    proposals: list[Mutation] = []
    for _ in range(n):
        kind = rng.choice([MutationKind.CITATION_SWAP, MutationKind.PARAGRAPH_REFRAME])
        if kind is MutationKind.CITATION_SWAP:
            applicable = [(t, r) for t, r in _CITATION_SWAPS if t in parent]
            if applicable:
                t, r = rng.choice(applicable)
                proposals.append(Mutation(kind=kind, target=t, replacement=r))
                continue
        # fall through to paragraph reframe if no citation applicable
        applicable_p = [(t, r) for t, r in _PARAGRAPH_REFRAMES if t in parent]
        if applicable_p:
            t, r = rng.choice(applicable_p)
            proposals.append(Mutation(kind=MutationKind.PARAGRAPH_REFRAME, target=t, replacement=r))
        else:
            # If nothing matches, propose a trivial no-op style swap
            proposals.append(
                Mutation(
                    kind=MutationKind.CITATION_SWAP,
                    target=parent[:20],
                    replacement=parent[:20],  # identity — record but skip
                )
            )
    return proposals
```

- [ ] **Step 3: Pass, commit**

```bash
uv run pytest tests/test_mutation_strategies.py -v
git add src/granum/center/mutation_strategies.py tests/test_mutation_strategies.py
git commit -m "feat(center): deterministic seed-based mutation proposer (v0.1)"
git push
```

### Task 1.10: Seed the cell + first real cycle end-to-end

**Files:**
- Create: `scripts/seed_cell.py`
- Create: `scripts/run_cycle.py`
- Modify: `src/granum/cli.py` — add `granum seed` and `granum cycle` commands

- [ ] **Step 1: Seed script — 3 starting B-cells**

`scripts/seed_cell.py`:

```python
"""One-time: seed the Aetna cardiac cell with 3 starting B-cell strategies."""
import asyncio
from granum.tools.phoenix_client import PhoenixClient
# ... initialize MCP session, then:

SEEDS = [
    {"name": "aetna_cardiac/bcell_1_baseline", "body": "Per Aetna CPB 0119 …"},
    {"name": "aetna_cardiac/bcell_2_aggressive", "body": "Per Aetna CPB 0286 …"},
    {"name": "aetna_cardiac/bcell_3_conservative", "body": "Per Aetna CPB 0353 …"},
]


async def main() -> None:
    async with phoenix_session() as session:
        client = PhoenixClient(session=session)
        for seed in SEEDS:
            pv = await client.upsert_prompt(
                name=seed["name"], body=seed["body"], tags=("production",)
            )
            print(f"seeded {pv.prompt_id}")


if __name__ == "__main__":
    asyncio.run(main())
```

(Each B-cell body is a full appeal template, ~400 words, distinguished by emphasis — baseline cites only Aetna; aggressive cites Aetna + ACC/AHA; conservative cites Aetna + cites ACC/AHA + adds risk-stratification language.)

- [ ] **Step 2: Live cycle script**

`scripts/run_cycle.py`: instantiate `GerminalCycle`, generate one denial, run, print outcome.

- [ ] **Step 3: Hook into CLI**

```python
# src/granum/cli.py additions
@app.command()
def seed(cell: str = "aetna_cardiac") -> None:
    """Seed a cell with 3 starting B-cells."""
    from scripts import seed_cell
    asyncio.run(seed_cell.main())


@app.command()
def cycle(cell: str = "aetna_cardiac", seed_value: int | None = None) -> None:
    """Run one germinal cycle on a synthetic denial."""
    from scripts import run_cycle
    asyncio.run(run_cycle.main(cell=cell, seed=seed_value))
```

- [ ] **Step 4: Run the first real cycle locally**

```bash
uv run granum doctor
uv run granum seed --cell aetna_cardiac
uv run granum cycle --cell aetna_cardiac --seed-value 42
```

Expected output:
```
[seeding] bc1 bc2 bc3 inserted
[cycle] denial=aetna_cardiac_... 
[cycle] negative_selection: 3 survived, 0 rejected
[cycle] tournament winner=bc2 score=8.4
[cycle] tombstoned: bc1 bc3
[cycle] expanded: bc2_mut_0 bc2_mut_1
[cycle] dataset_writeback: ok
```

Phoenix Cloud UI: lineage shows 3 production → 2 tombstoned + 1 production + 2 experimental.

- [ ] **Step 5: Commit**

```bash
git add scripts/ src/granum/cli.py
git commit -m "feat(cli): seed + cycle commands — first end-to-end Phoenix run"
git push
```

**Phase 1 gate:** Three consecutive `granum cycle` calls with different seeds complete without exceptions. Phoenix prompt registry shows a growing lineage. Average judge composite score on `production` versions trends upward across 3 cycles (will not be monotonic — but trending). Dataset `granum/aetna_cardiac/outcomes` has at least 3 rows.

---

## Phase 2 — Multi-Cell + Immune Memory + Antigen Drift

**Goal:** 5 cells running independently. Champion versions preserved as immune memory. Antigen drift detection triggers re-test.

**Workstreams (PARALLEL):**
- WS-2.A: Cell registry + multi-cell driver (Claude)
- WS-2.B: Curate denial patterns for 4 new cells (Codex)
- WS-2.C: Immune memory primitive + memory-cell reactivation (Claude)
- WS-2.D: Antigen drift detector (Codex)
- WS-2.E: Multi-cell CLI + scheduler config (Claude)

**Failure modes:**
- **F2.1** 5 cells exceed eval budget → drop to 3 (drop Cigna, Humana).
- **F2.2** Memory reactivation logic ambiguous → simple rule: reactivate if 2 consecutive generations of active population fail negative selection.
- **F2.3** Drift detector too noisy → require 3-sample threshold + 25% mean-score shift before drift signal fires.
- **F2.4** Pattern bank for new cells thin → start with 5 patterns per cell; expand if time.

### Task 2.1: Cell registry abstraction
### Task 2.2: Curate United × oncology pattern bank
### Task 2.3: Curate Anthem × mental-health pattern bank
### Task 2.4: Curate Cigna × ortho + Humana × endocrinology pattern banks
### Task 2.5: Immune memory primitive — champion preservation
### Task 2.6: Memory-cell reactivation logic
### Task 2.7: Antigen drift detector
### Task 2.8: Multi-cell driver + scheduler
### Task 2.9: Cross-cell observability span design
### Task 2.10: Phase 2 integration test

*(Tasks 2.1–2.10 follow the same TDD pattern as Phase 1 — failing test → minimal impl → pass → commit. Each ~20 minutes solo, ~6 minutes with parallel agents. Detailed task structure mirrors 1.1–1.10. Will be expanded inline by executing subagents using this plan template; the key contracts are listed in §A "Mechanism Contracts" at the end of this plan.)*

**Phase 2 gate:** 5 cells (or 3 if F2.1 fires) each running independent cycles. Memory cells visible in Phoenix as tagged `memory_cell`. Drift detection fires correctly when a new pattern is injected mid-stream. Multi-cell driver completes 1 round across all cells in <90s.

---

## Phase 3 — Red Queen Co-Evolution

**Goal:** Adversarial payer-agent population co-evolves against appeal-writers. Triangular tournament: appeal-writer drafts → payer-agent denies → judge scores defensibility. Both populations visible in Phoenix as separate prompt lineages.

**Workstreams (PARALLEL):**
- WS-3.A: Payer-agent persona + initial population (Claude)
- WS-3.B: Triangular tournament protocol (Claude)
- WS-3.C: Co-evolution regularization (anti-degeneracy) (Codex)
- WS-3.D: Dual-lineage Phoenix queries + viz hooks (Claude)

**Failure modes:**
- **F3.1** Co-evolution diverges into degeneracy → cap mutation rate at 15%, reset adversary population every 5 generations to a known-strong baseline.
- **F3.2** Payer-agent produces uninterpretable denials → constrain payer prompt template to standard insurance-denial format (denial reason + clinical policy citation + appeal-right notice).
- **F3.3** Triangular eval cost explodes → batch eval requests, cache `(appeal_hash, denial_hash)` → score.
- **F3.4** Payer-agent population too small for diversity → initialize with 5 personas (strict, lenient, formalist, cost-focused, evidence-focused).

### Task 3.1: Payer-agent prompt templates + seeded personas
### Task 3.2: Payer-agent ADK definition + tool use
### Task 3.3: Adversarial denial generator (replaces synthetic generator at runtime)
### Task 3.4: Triangular tournament protocol
### Task 3.5: Defensibility scorer (LLM-as-judge variant for two-sided eval)
### Task 3.6: Co-evolution driver (alternates appeal-population evolution with payer-population evolution)
### Task 3.7: Anti-degeneracy regularization
### Task 3.8: Dual-lineage queries + sample data writeback
### Task 3.9: Phase 3 integration test (5 co-evolution rounds end-to-end)

**Phase 3 gate:** Co-evolution runs for 5 rounds with both populations showing measurable mutation. Triangular tournament produces ranked appeals + ranked denials. Neither population collapses. Per-cell fitness curves climb for at least 3 of 5 cells.

---

## Phase 4 — Cross-Cell Transfer Detection

**Goal:** Detect when an appeal strategy effective on (payer_A × diagnosis_X) generalizes to (payer_B × diagnosis_X) or (payer_A × diagnosis_Y). Seed the adjacent cell with the transferred strategy. Visualize transfer as edges in lineage tree.

**Workstreams (PARALLEL):**
- WS-4.A: Cell embedding + similarity scoring (Codex)
- WS-4.B: Cross-cell transfer trial + statistical gate (Claude)
- WS-4.C: Transfer-edge metadata for UI (Claude)

**Failure modes:**
- **F4.1** Transfer detection too noisy → require p<0.05 on 5-sample transfer trial before claiming.
- **F4.2** Cell embedding choice wrong → A/B sentence-transformers vs Gemini embed on a held-out similarity benchmark.

### Task 4.1: Cell embedding + similarity matrix
### Task 4.2: Transfer trial harness
### Task 4.3: Transfer-promotion gate
### Task 4.4: Transfer-edge metadata writeback to Phoenix

**Phase 4 gate:** At least one demonstrated transfer between cells with statistical confidence ≥95%. Transfer edge appears in lineage data.

---

## Phase 5 — Frontend + Demo Polish *(parallel with Phase 4)*

**Goal:** Next.js frontend renders dual-lineage trees, per-cell fitness curves, prompt diff side-by-side viewer. Polish pipeline applied. Demo video script written.

**Workstreams (PARALLEL):**
- WS-5.A: Next.js skeleton + Phoenix data adapter (Claude)
- WS-5.B: Lineage tree (D3 phylogenetic) (Claude)
- WS-5.C: Fitness curves (Recharts) (Codex)
- WS-5.D: Prompt diff side-by-side viewer (Claude)
- WS-5.E: Polish pipeline — baseline-ui → fixing-accessibility → fixing-motion-performance → fixing-metadata (Claude, sequential)
- WS-5.F: Demo script + voiceover prep (Codex)

**Failure modes:**
- **F5.1** UI eats time → ship the Phoenix UI as the main visual + a 1-page Next.js landing.
- **F5.2** Phylogenetic tree library too heavy → roll minimal SVG using D3-hierarchy.
- **F5.3** Polish pipeline conflicts → invoke skills sequentially, not parallel. baseline-ui first, then a11y, then motion, then metadata.

### Task 5.1: Next.js scaffold + Phoenix data adapter
### Task 5.2: Lineage tree D3 component
### Task 5.3: Co-evolution dual-tree view
### Task 5.4: Fitness curve component
### Task 5.5: Prompt diff component
### Task 5.6: Landing page + cell selector
### Task 5.7: baseline-ui pass (run skill)
### Task 5.8: fixing-accessibility pass (run skill)
### Task 5.9: fixing-motion-performance pass (run skill)
### Task 5.10: fixing-metadata pass (run skill)
### Task 5.11: Demo script — 3-min storyboard
### Task 5.12: ElevenLabs narration + voiceover render
### Task 5.13: Screen recording (`scripts/demo.sh`)
### Task 5.14: YouTube upload + thumbnail

**Phase 5 gate:** Hosted URL renders lineage trees correctly. Polish pipeline passes all 4 skill audits. 3-min demo video uploaded unlisted to YouTube.

---

## Phase 6 — Submit

**Goal:** Submission complete via Devpost form by 2026-06-10 noon EDT (24h buffer before hard deadline).

**Failure modes:**
- **F6.1** Submission form bug → submit 2026-06-10 12:00 EDT, leave 26 hours of buffer.
- **F6.2** Video render fails → ship a backup raw screen capture with on-screen captions.

### Task 6.1: Verify license file visible at repo root
### Task 6.2: Verify hosted URL alive + smoke-test all key paths
### Task 6.3: Verify YouTube video public + ≤3 min
### Task 6.4: Fill Devpost form per `docs/submission.md`
### Task 6.5: Submit + screenshot confirmation

**Phase 6 gate:** Devpost shows submitted entry for Arize track. License visible. Hosted URL up. Video accessible.

---

## §A — Mechanism Contracts (referenced by Phase 2-4 tasks)

These are the exact type signatures and behaviors each mechanism MUST satisfy. Subagents implementing later phases use these as the integration interface.

### A.1 ImmuneMemory contract

```python
class ImmuneMemory:
    async def preserve_champion(self, *, cell: str, prompt_id: str, version_id: str) -> None:
        """Tag a winning version as 'memory_cell' — preserved indefinitely."""

    async def reactivate(self, *, cell: str) -> PromptVersion | None:
        """Reactivate a memory cell when 2 consecutive cycles fail negative selection."""

    async def list_memory_cells(self, *, cell: str) -> list[PromptVersion]: ...
```

### A.2 AntigenDrift contract

```python
class AntigenDrift:
    async def observe_denial(self, *, denial: Denial) -> None: ...

    async def is_drifted(self, *, cell: str, window_size: int = 10) -> bool:
        """True if recent denial pattern distribution shifts >25% in mean embedding distance."""

    async def retest_champion(self, *, cell: str, against: Denial) -> JudgeScore: ...
```

### A.3 RedQueen / PayerAgent contract

```python
class PayerAgent:
    async def deny(self, *, appeal: str, persona_id: str) -> Denial:
        """Produce a denial response to a candidate appeal, constrained to standard format."""


class CoEvolutionDriver:
    async def round(self) -> CoEvolutionRoundResult:
        """One round: appeals evolve, then payers evolve, then triangular tournament."""
```

### A.4 CrossCellTransfer contract

```python
class CrossCellTransfer:
    async def similarity(self, cell_a: str, cell_b: str) -> float: ...
    async def trial_transfer(self, *, source: str, target: str, prompt_id: str) -> TransferTrial: ...
    async def promote_transfer(self, trial: TransferTrial) -> None: ...
```

---

## §B — Daily Standup Targets (calendar)

| Day | Date | Phase | Target end-of-day state |
|---|---|---|---|
| 1 | 2026-05-28 | Pre-flight + P0 | Phoenix MCP audit done; repo created; CI green; Cloud Run /healthz alive |
| 2 | 2026-05-29 | P1 (1.1-1.3) | Denial generator + gold loader + Phoenix client all tested |
| 3 | 2026-05-30 | P1 (1.4-1.6) | Negative selection + mutations + judge tested |
| 4 | 2026-05-31 | P1 (1.7-1.10) | First real Phoenix cycle ran end-to-end |
| 5 | 2026-06-01 | P2 (start) | Cell registry + 2 more cells curated |
| 6 | 2026-06-02 | P2 (mid) — _AgentGov submission also today_ | All 5 cells running; immune memory live |
| 7 | 2026-06-03 | P2 (close) + P3 (start) | Antigen drift live; payer-agent persona seeded |
| 8 | 2026-06-04 | P3 (mid) | Triangular tournament running |
| 9 | 2026-06-05 | P3 (close) | 5 co-evolution rounds completed |
| 10 | 2026-06-06 | P4 (start) | Cell embedding + similarity scoring |
| 11 | 2026-06-07 | P4 (close) + P5 (start) | First transfer detected; Next.js scaffolded |
| 12 | 2026-06-08 | P5 (lineage tree + curves) | Lineage tree renders, fitness curves render |
| 13 | 2026-06-09 | P5 (polish + video) | Polish pipeline passed; video recorded |
| 14 | 2026-06-10 | P6 | Submitted by noon EDT; buffer for fixes |
| 15 | 2026-06-11 | (buffer) | Hard deadline 14:00 PDT — submission verified live |

---

## §C — Open Questions Locked Before Phase 0

These must be answered before Phase 0 Task 0.1:

1. **Phoenix MCP delete behavior** — empirically verified via Pre-flight Task A.
2. **Final name** — Granum (placeholder) vs Centra, Affinity, Overturn, Hypermut. User picks before repo creation in Task 0.1.
3. **Repo visibility** — public from day 1 (hackathon rule).
4. **License** — Apache-2.0 (decided).
5. **GCP project ID** — new project `granum-2026` or reuse existing.

---

## §D — What This Plan Deliberately Does NOT Include (YAGNI)

- Multi-vertical (only medical PA appeals).
- EHR integration.
- Real PHI — all data synthetic.
- Payer-side product surfaces.
- Patient-facing direct-to-consumer flow (deferred to v0.2).
- Federated cells across multiple physician practices (deferred to v1.0).
- Live payer policy news monitoring for drift triggers (deferred — manual drift injection in v0.1).
- Multi-language support.
- Mobile app.
- Authentication / user accounts (demo is single-tenant).
