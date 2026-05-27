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
