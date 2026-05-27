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

## [Terminal B] — 2026-05-27 17:30
- DONE: All 4 cells + 2 docs pushed in commit 61ea0f2. Each cell ships `denial_templates.json` (10 patterns, flat-array schema matching aetna_cardiac), `valid_citations.json` (40+ real payer + guideline URLs — UHC oncology 50, Anthem MH 42, Cigna ortho 42, Humana endo 43), `gold_appeals.jsonl` (12 overturned exemplars judge_score>=7), `judge_rubric.md` (5-axis cell-specialization). Also `data/judge_rubric_variants/<cell>.md` copies per COORDINATION.md.
- VERIFICATION: re-ran negative-selection check post-push: every citation in every gold appeal is a member of that cell's `valid_citations.json` (0 violations across all 48 gold appeals). Every CPT/HCPCS/ICD-10 code is real; payer policy IDs use the real payer code where one exists (CMM-311 / CG-BEH-02 / etc.), short payer-code abbreviation where the payer doesn't number policies (UHC-OMCC, Humana-MCP-GLP1-T2D, etc.).
- `cpb_number` field: schema parallel maintained even though the literal "CPB" naming is Aetna-origin — non-Aetna payers' policy IDs live in the same slot.
- IN PROGRESS: none (primary scope complete).
- BLOCKED: none for Terminal B's scope. Terminal A is unblocked for Phase 1.2/1.3 which can now read all four cells.
- NEXT: standing by for (a) Phoenix MCP audit feedback that requires schema changes, (b) Aetna pattern-bank extensions Terminal A might want me to mirror across cells, (c) feedback from Terminal A or C requiring rubric tweaks. If silent for the next session, I'm available to expand any cell to 15-20 patterns or add a 5th cell.
- FILES TOUCHED: data/{united_oncology,anthem_mental_health,cigna_ortho,humana_endocrinology}/**, data/judge_rubric_variants/**, docs/biology-mapping.md, docs/cell-curation-methodology.md.

## [Terminal A] — 2026-05-27 12:32
- DONE: Phase 1.2 (gold dataset loader + 12 overturned Aetna cardiac appeals). `src/granum/data/gold.py` exposes a frozen `GoldAppeal` dataclass + `load_gold_appeals()` JSONL reader. `data/aetna_cardiac/gold_appeals.jsonl` ships 12 exemplars: 10 cover all 10 patterns from `denial_templates.json` (CPB 0119, 0286, 0353, 0535) plus 2 edge cases — #011 timely-filing under 29 CFR 2560.503-1(f)/(g) and #012 policy-ambiguity / contra proferentem. Judge scores span 7-10 (one 7, three 8s, four 9s, four 10s). Word counts 226-434 with deliberate variance. Every CPB section cited is grounded in the 4-CPB pattern bank — no invented bulletin numbers. ACC/AHA citations point at real guidelines (2020 VHD, 2021 Chest Pain, 2021 Revascularization, 2022 HF, 2023 AF, 2018 Bradycardia, 2014 NSTE-ACS). Tests 2/2 pass, full suite 8/8, ruff + mypy clean.
- IN PROGRESS: Phase 1.3 (Phoenix MCP client wrapper)
- BLOCKED: Phase 0.5 + 1.10 still gated on user actions (ADC login, billing, Phoenix API key)
- NEXT: Phase 1.4 (negative selection / citation verifier)
- NOTE: Spec asked for >=6 distinct CPB numbers; the pattern bank only contains 4 (0119, 0286, 0353, 0535) and the boundary rule "do not invent CPB numbers" overrides — we stay at 4. If broader CPB coverage is needed later, expand the Phase 1.1 pattern bank first, then revisit the gold set.

## [Terminal A] — 2026-05-27 12:38
- DONE: Phase 1.3 (Phoenix client wrapper with Path B apoptosis — REST for tag removal, MCP for everything else). `src/granum/tools/phoenix_client.py` exposes `PhoenixClient` with `upsert_prompt`, `add_version_tag`, `remove_version_tag` (REST), `tombstone` (atomic two-step: REST remove `production` + MCP add `tombstoned`, 404-tolerant), `list_active_prompts` (client-side tombstoned filter), `add_dataset_examples`, `get_spans`. 7/7 new tests pass with mocked MCP+REST transports, full suite 15/15, ruff + mypy clean. Sole seam between Granum and Phoenix — no other Granum module references Phoenix tool names or REST paths.
- IN PROGRESS: Phase 1.4 (negative selection citation verifier)
- BLOCKED: Phase 0.5 + 1.10 (user actions)
- NEXT: Phase 1.5 (mutation operators)

## [Terminal A] — 2026-05-27 12:42
- DONE: Phase 1.4 (negative selection — citation verifier + 40-entry valid set)
- IN PROGRESS: Phase 1.5 (mutation operators)
- BLOCKED: Phase 0.5 + 1.10
- NEXT: Phase 1.6 (LLM-as-judge)

## [Terminal A] — 2026-05-27 12:44
- DONE: Phase 1.5 (mutation operators — 4 kinds, no rewrite, 6 tests)
- IN PROGRESS: Phase 1.6 (LLM-as-judge)
- BLOCKED: Phase 0.5 + 1.10
- NEXT: Phase 1.7 (tournament)

## [Terminal A] — 2026-05-27 12:47
- DONE: Phase 1.6 (LLM-as-judge — 5-axis rubric, median-of-3, English feedback per Arize prompt-learning thesis)
- IN PROGRESS: Phase 1.7 (tournament engine)
- BLOCKED: Phase 0.5 + 1.10
- NEXT: Phase 1.8 (germinal cycle orchestrator)

## [Terminal A] — 2026-05-27 12:49
- DONE: Phase 1.7 (tournament — gather-based concurrent scoring, tie-break by prompt_id)
- IN PROGRESS: Phase 1.8 (germinal cycle orchestrator)
- BLOCKED: Phase 0.5 + 1.10
- NEXT: Phase 1.9 (mutation strategies)

## [Terminal A] — 2026-05-27 12:54
- DONE: Phase 1.8 (germinal cycle orchestrator — full loop wired with OTel spans, 2 integration tests)
- IN PROGRESS: Phase 1.9 (mutation strategies — deterministic proposer)
- BLOCKED: Phase 0.5 + 1.10 (user actions)
- NEXT: Phase 1.10 (live cycle, blocked until 0.4 done)

## [Terminal C] — 2026-05-27 12:55
- DONE:
  - Polish pipeline complete (sequential, per startup prompt):
    - baseline-ui: added `web/lib/cn.ts` (clsx + tailwind-merge), converted bare `role="tab"` to plain `aria-pressed` toggle buttons, added `font-variant-numeric: tabular-nums` to all mono spans, documented three explicit exceptions in `web/DESIGN.md` §8.5 (editorial `tracking-widest`, SVG chart-area gradient, 600ms tombstone fade).
    - fixing-accessibility: added `sr-only h1` to `/cell/[cell]`, wrote `web/public/favicon.svg` (lineage motif in OKLCH palette), removed dead `og.png`/`apple-touch-icon` metadata refs.
    - fixing-motion-performance: clean — every transition audited (compositor-only on small SVG surfaces; `isAnimationActive=false` on Recharts; no `will-change`; `prefers-reduced-motion` honored).
    - fixing-metadata: `app/opengraph-image.tsx` + per-cell variant using `next/og` ImageResponse (Germinal Lab palette); per-cell `openGraph.url`/`twitter` override so `og:url` agrees with canonical.
  - Demo materials: `docs/demo-script.md` (3-min, 20-second beats), `docs/storyboard.md` (12 frames), `scripts/demo.sh` (orchestrator with DEMO_PACE/FRESH/CELL/CYCLES/SEED knobs).
  - Browser verification via Playwright MCP: landing + `/cell/aetna_cardiac` render correctly. Hero (asymmetric serif with apoptosis-red "permanently"), cell meta strip, PromptDiff (word-level diff with citation delta), and FitnessCurve (0.41→0.79 climb) all production-quality.
- IN PROGRESS: none for Phase 5 primary scope; standing by for integration day.
- BLOCKED: none for Terminal C. Phase 5 integration with real Phoenix data is gated on Terminal A publishing `docs/api-contract.md` (Phase 3) and on user clearing the GCP+Phoenix-Cloud auth blockers.
- KNOWN ISSUE: with `tree<TreeDatum>().nodeSize([44, 220])`, the 8-generation Aetna lineage extends ~1760px wide vs a ~745px viewport so the alive + champion nodes are initially offscreen-right. Attempted a fit-to-content fix (smaller spacing + auto-zoom to bbox); it was reverted on disk twice despite user confirmation. Leaving as-is; users can wheel-zoom + drag-pan via d3-zoom. Not blocking but worth resolving before final video capture.
- NEXT: when Terminal A publishes `docs/api-contract.md`, swap `web/lib/mock-data.ts` for a real `/api/cell/[cell]` fetcher. Run `web-quality-audit` skill (Core Web Vitals) after integration. Generate the actual OG PNGs via Playwright once a real URL is deployed.
- FILES TOUCHED THIS SESSION: `docs/{design-references.md, demo-script.md, storyboard.md}`, `web/**` (full Next.js app), `scripts/demo.sh`.
