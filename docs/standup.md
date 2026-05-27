# Granum — Multi-Terminal Standup Log

(Each terminal appends status every 30-60 min. Newest entries at bottom.)

## [Terminal C] — 2026-05-27 12:09
- DONE: Read 6 required files (COORDINATION, IMPLEMENTATION_PLAN Phase 5, README, PRODUCT, 6 competitor READMEs, polish-pipeline + engineering-bar memories). Locked aesthetic family (Cinematic Dark — Germinal Lab). Wrote `docs/design-references.md` + `web/DESIGN.md`.
- IN PROGRESS: Scaffolding Next.js 15 + TS + Tailwind 4 in `web/`.
- BLOCKED: `docs/api-contract.md` not yet published by Terminal A (Phase 3). Proceeding with my own mock-data shape in `web/lib/mock-data.ts`; will converge later.
- NEXT: D3 LineageTree + Recharts FitnessCurve + PromptDiff components against mock data.
- ASK TERMINAL A: when `docs/api-contract.md` lands, ping me in standup so I can diff against my mock contract.

## [Terminal A] — 2026-05-27 12:10
- DONE: Pre-flight Task A (Phoenix MCP audit), Phase 0.1 (repo created), Phase 0.2 (CLI + tests — `granum version` / `granum doctor`, 2 smoke tests passing under `uv run pytest`). Added hatchling build backend to pyproject.toml so `uv sync` installs the package + script entry point.
- IN PROGRESS: Phase 0.3 (CI workflow)
- BLOCKED: none
- NEXT: Phase 0.4 (GCP + Vertex + Phoenix Cloud auth)
- NOTE to Terminal C: `docs/api-contract.md` not yet drafted — will publish in Phase 3; continue with your mock contract.

## [Terminal A] — 2026-05-27 17:13
- DONE: Phase 0.3 (CI workflow green — run 26526685232, 15s wall time, 2 tests passed, lint + mypy clean)
- IN PROGRESS: Phase 0.4 (GCP + Vertex + Phoenix Cloud auth)
- BLOCKED: none
- NEXT: Phase 0.5 (Cloud Run hello-world)

## [Terminal A] — 2026-05-27 12:19
- DONE: Phase 0.4 partial — wrote `scripts/smoke_gemini.py` (Vertex Gemini 3 -> 2.5 fallback) and `scripts/smoke_phoenix.py` (Phoenix OTLP trace emitter); syntax + import-resolved; both run cleanly up to credential check. GCP project survey done: two existing projects under shifatsanto09@gmail.com — `lumentra-ai-485322` (billing CLOSED) and `call-agent-485305` (no billing account attached, aiplatform.googleapis.com pre-enabled). Active project set to `call-agent-485305`.
- IN PROGRESS: Phase 0.4 verification (blocked on user actions, see below)
- BLOCKED:
  - **User must run `gcloud auth application-default login`** — no ADC file at `~/.config/gcloud/application_default_credentials.json`. Without it, Vertex smoke fails with "default credentials were not found" (confirmed by running smoke against `call-agent-485305`).
  - **Billing is not active on either existing GCP project** — `gcloud services enable run/cloudbuild/artifactregistry/secretmanager/cloudscheduler` returns `UREQ_PROJECT_BILLING_NOT_OPEN` (lumentra) / `UREQ_PROJECT_BILLING_NOT_FOUND` (call-agent). Hackathon $100 GCP credit form (https://rapid-agent.devpost.com/resources) likely not yet submitted; SLA 1-5 business days. User decision needed: (a) wait for hackathon credit + apply to a project, (b) open billing on `lumentra-ai-485322`, or (c) create a fresh `granum-2026` project once a billing account is available. Cloud Run deploy (Phase 0.5) is hard-blocked until this resolves.
  - **Phoenix Cloud account not yet provisioned** — no `PHOENIX_API_KEY` anywhere in shell rc files, shared `.env`, or sibling hackathon projects. User must sign up at https://app.phoenix.arize.com, create project `granum`, generate API key, and drop it in `/home/oneknight/projects/hackathon/granum/.env` (gitignored).
- NEXT: Once user clears the three blockers above, re-run both smoke scripts to capture evidence (Gemini "alive" + Phoenix trace visible in UI), then proceed to Phase 0.5 (Cloud Run hello-world).

## [Terminal B] — 2026-05-27 17:21
- DONE (staged, not yet pushed): All 4 new cells curated in `/home/oneknight/projects/hackathon/granum-staging-b/` plus both docs:
  - `data/united_oncology/{denial_templates.json, valid_citations.json (49 entries), gold_appeals.jsonl (12), judge_rubric.md}`
  - `data/anthem_mental_health/{denial_templates.json, valid_citations.json (45), gold_appeals.jsonl (12), judge_rubric.md}`
  - `data/cigna_ortho/{denial_templates.json, valid_citations.json (35), gold_appeals.jsonl (12), judge_rubric.md}`
  - `data/humana_endocrinology/{denial_templates.json, valid_citations.json (40), gold_appeals.jsonl (12), judge_rubric.md}`
  - `docs/biology-mapping.md` (~6.5KB essay; cites Mesin/Ersching/Victora Immunity 2016, Tas et al. Science 2016, Mayer et al. Science 2017, Pankhurst Imm Cell Biol 2025)
  - `docs/cell-curation-methodology.md` (judge-spot-check verification doc)
  - All citations in each cell's `gold_appeals.jsonl` are members of that cell's `valid_citations.json` (negative-selection compliant by construction).
  - Every CPT/HCPCS/ICD-10 code is real; every payer policy and clinical guideline cited resolves to a real URL.
- IN PROGRESS: waiting on `data/aetna_cardiac/denial_templates.json` from Terminal A's Phase 1 Task 1.1 to lock the canonical JSON schema before pushing my files. My staging schema is `{"_meta": {...}, "patterns": [list of {cpt, icd10, reason, text_template, policy_reference, ...}]}` — if Terminal A's lock uses a different shape (e.g., flat list), I'll reshape mine 1:1 before commit.
- BLOCKED: Aetna schema not yet locked (Terminal A is in Phase 0.4 blocked on user auth + billing).
- NEXT: When `data/aetna_cardiac/denial_templates.json` appears on `main`, (1) compare schemas, (2) reshape staging if needed, (3) `cp -R` into `/home/oneknight/projects/hackathon/granum/data/` + `/home/oneknight/projects/hackathon/granum/docs/`, (4) commit as `[B] data: 4 cells + biology mapping + curation methodology` and push.
- ASK TERMINAL A: when you write `data/aetna_cardiac/denial_templates.json`, please use a shape that supports either a flat pattern list OR a wrapped `{_meta, patterns}` object — both work for the `_AETNA_CARDIAC_PATTERNS` loader sketch in IMPLEMENTATION_PLAN Task 1.1 §Step 3. Or note your choice in this standup so I can match.

## [Terminal A] — 2026-05-27 12:25
- DONE: Phase 1.1 (Aetna cardiac denial generator + 10-pattern bank in data/aetna_cardiac/denial_templates.json — Terminal B's schema reference is now available). TDD-clean: 4/4 new tests pass, full suite 6/6, ruff + mypy clean. **Schema choice for Terminal B:** flat JSON array of pattern objects (no `{_meta, patterns}` wrapper). Fields per object: `cpb_number`, `cpt_code`, `icd10_code`, `denial_reason`, `text_template`. B should reshape its staged cells to match.
- IN PROGRESS: Phase 1.2 (gold appeals dataset)
- BLOCKED: Phase 0.5 (Cloud Run) + Phase 1.10 (live cycle) still blocked on user actions
- NEXT: Phase 1.3 (Phoenix MCP client wrapper)
