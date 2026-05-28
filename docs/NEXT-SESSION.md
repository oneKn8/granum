# NEXT-SESSION.md — Granum Hackathon Handoff

**Frozen at:** 2026-05-27 ~13:15 (Terminal A's clock)
**Hackathon deadline:** 2026-06-11 14:00 PDT (Google Cloud Rapid Agent Hackathon, Arize Phoenix track)
**Repo:** https://github.com/oneKn8/granum — Apache-2.0, public, CI green
**Local path:** `/home/oneknight/projects/hackathon/granum/`
**Build state:** **60/60 tests passing on main**

This file is the cold-resume document. Read it top-to-bottom and you have full context to pick up.

---

## ⚠️ STEP ZERO #1 — PhoenixClient schema retrofit (Phase 1.10b) is the next code task

**Status check (2026-05-28 ~13:50):**
- GCP `granum-2026` project + billing OPEN + all 6 APIs enabled. ADC + quota project set. Vertex Gemini 3.1 Pro Preview + Gemini 3.5 Flash both verified live.
- Phoenix Cloud space at `https://app.phoenix.arize.com/s/shifatislamsanto764` — API key in local `.env` (gitignored), `smoke_phoenix.py` emits traces successfully.
- `phoenix_session.py` bootstrap spawns `@arizeai/phoenix-mcp` over stdio + REST httpx with Bearer auth. Live MCP smoke confirmed: `list_active_prompts(name_prefix="aetna_cardiac/")` returns 0 against the empty space.

**But:** first live `upsert-prompt` call exposed that Phase 1.3's `PhoenixClient` was authored against a fictional MCP schema. The Phoenix MCP audit (2026-05-27) captured tool *names* + *descriptions* but not per-tool argument schemas or response shapes. Four mismatches:

1. `upsert-prompt` requires `template` (not `body`).
2. `upsert-prompt` has NO `tags` parameter (tags must be applied after via `add-prompt-version-tag`).
3. Response keys are `id` / `name` / `description`, not `promptId` / `versionId`. The response is text-prefixed (`Successfully created prompt "X":` then a JSON blob).
4. Prompt names get `/` stripped — `aetna_cardiac/bcell_1` becomes `aetna_cardiacbcell_1`.

**Phase 1.10b work needed (~30–45 min agent time):**
- Run `session.list_tools()` for the 10 prompt tools + 7 dataset tools + 8 tracing tools we'll actually call. For each, capture the full `inputSchema` and one real-invocation response. Write `research/phoenix-mcp-schemas.md`.
- Retrofit `src/granum/tools/phoenix_client.py`:
  - `upsert_prompt(name, template, tags=...)` (was `body`) — internally calls `upsert-prompt` then `add-prompt-version-tag` once per tag.
  - Change response parsing to read `id` from the text-wrapped JSON, not `promptId`.
  - Document the slash-stripping; either pick a new naming scheme (underscores: `aetna_cardiac__bcell_1`) or compute the namespace some other way.
  - `list_active_prompts` to handle bare-array MCP responses.
- Update the 7 PhoenixClient unit tests to use the real shape.
- Re-run `scripts/seed_cell.py` against the live space; expect 3 B-cells in Phoenix UI.
- Then `Phase 1.10c`: first live `granum cycle --cell aetna_cardiac --seed-value 42`.

**See:** `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-audit-schemas-not-just-names.md` — the permanent lesson saved from this gap.

---

## ⚠️ STEP ZERO #2 — Set up git worktrees BEFORE any other work

In the 2026-05-27 session, three scope leaks occurred where one terminal's commit swept in other terminals' WIP files. Root cause: all three Claude sessions ran in the SAME working directory at `/home/oneknight/projects/hackathon/granum/`, sharing one git index. The leaks weren't bugs — they were the predictable consequence of shared-index multi-terminal work.

**Fix for the next session: each terminal works in its own `git worktree`.** Separate working dir + separate index per terminal. No sweep possible.

Before any of the three terminals starts work, ONE terminal (recommend Terminal A) runs:

```bash
cd /home/oneknight/projects/hackathon/granum
git worktree add ../granum-A -b session-A main   # Terminal A's worktree on a new branch
git worktree add ../granum-B -b session-B main   # Terminal B's worktree
git worktree add ../granum-C -b session-C main   # Terminal C's worktree
git worktree list
```

Then each terminal `cd`'s to its own worktree:
- Terminal A: `cd /home/oneknight/projects/hackathon/granum-A`
- Terminal B: `cd /home/oneknight/projects/hackathon/granum-B`
- Terminal C: `cd /home/oneknight/projects/hackathon/granum-C`

Each runs work on its own branch (`session-A`, `session-B`, `session-C`). Periodically rebase against main, then push the branch + open a merge to main when a phase completes:

```bash
# inside e.g. granum-A
git fetch origin
git rebase origin/main
git push -u origin session-A
gh pr create --base main --head session-A --title "Phase 3: …" --body "…"
gh pr merge --merge --auto    # or --rebase
```

Or for trivial commits (standup updates, env tweaks), just `git push origin session-A:main` if branch is fast-forward. PRs are safer for code changes.

When a worktree is no longer needed: `git worktree remove ../granum-A` (and `git branch -d session-A` once merged).

---

## Read these first (in order)

1. This file
2. `docs/COORDINATION.md` — multi-terminal scope split rules
3. `docs/IMPLEMENTATION_PLAN.md` — the full phased plan
4. `docs/PRODUCT.md` — what Granum is and why
5. `docs/api-contract.md` — JSON shapes for the FastAPI server
6. `research/phoenix-mcp-audit.md` — empirical Phoenix MCP capability matrix; locks Path B for apoptosis
7. `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-git-commit-email.md` — **CRITICAL** git identity rule
8. `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-personal-cloud-identities.md` — safe email matrix for git/gcloud/gh
9. `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-git-commit-scope.md` — **CRITICAL** scope-leak rule + the worktree fix
10. `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-verify-model-names-and-apis.md` — verify current canonical model/API names before reporting "blocked"
11. `~/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-audit-schemas-not-just-names.md` — **CRITICAL** when auditing an MCP/API, capture per-tool schemas + response shapes, not just operation names

---

## Hard rules that bit us in this session — do not repeat

1. **Set up worktrees FIRST.** See Step Zero above. Three scope leaks happened in this session because we didn't.
2. **Never override `git user.email` on commit.** Repo's local config is authoritative: `shifatislamsanto764@gmail.com` (Shifat's personal identity, linked to `oneKn8`). Do NOT pass `-c user.email=contact@rhemicai.com` or any other override. The `contact@rhemicai.com` address from auto-memory is the Rhemic AI ORG email, NOT personal-repo identity. Terminal B violated this in this session; force-push fixed it but bad SHAs persist in GitHub GC window.
3. **`env -u PYTHONPATH` prefix needed for local pytest runs** on this machine. ROS Humble pollutes Python path. CI doesn't have this problem.
4. **Always `git status` + `git diff --cached --stat` BEFORE `git commit`.** Even with worktrees, verify exact staged scope before every commit. `git add <file>` alone is NOT sufficient.
5. **Phoenix prompt versions are immutable.** No `delete-prompt-version`. Apoptosis is Path B: REST removes `production` tag, MCP adds `tombstoned` tag. `PhoenixClient.tombstone(prompt_id, version_id)` does both.
6. **`add-prompt-version-tag` is move-semantic** in Phoenix MCP — re-tagging strips from prior version. Atomic champion-swap primitive.
7. **For novelty work,** read `~/.claude/projects/.../memory/feedback-explore-like-human-not-weights.md` BEFORE brainstorming. Don't generate ideas from Claude reflexes; spawn research into far fields.
8. **GCP setup is DONE.** Project `granum-2026`, billing `01D7E1-9DABE7-254A06` OPEN, all 6 APIs enabled. ADC + quota project set. `.env` populated locally with PHOENIX_API_KEY + Vertex env vars + the verified model IDs (`gemini-3.1-pro-preview` for reasoning, `gemini-3.5-flash` for fast). `.env` is gitignored — never commits.
9. **Phoenix Cloud is DONE.** Space at `https://app.phoenix.arize.com/s/shifatislamsanto764`, System API Key created and stored in local `.env`, smoke trace verified in UI. Don't ask the user to re-do these steps.
10. **PhoenixClient was authored against a fictional schema.** See Step Zero #1 above. The mocked unit tests still pass; real MCP rejects the calls. Do NOT trust the existing 7 PhoenixClient tests as integration evidence — they only verify the mock contract. Phase 1.10b lifts that into a verified-live contract.
11. **`gemini-3-pro` was DISCONTINUED March 2026.** Use `gemini-3.1-pro-preview` (primary) + `gemini-3.5-flash` (fast). Pinned in `.env.example`. Don't probe for `gemini-3-pro` — it 404s in all regions for valid reasons.

---

## What's done (this session)

### Pre-flight + Phase 0 — Foundation
- ✅ Phoenix MCP capability audit (`research/phoenix-mcp-audit.md`, 27 tools, Path B locked) — names captured, schemas NOT captured (the gap that bit us on 2026-05-28; see Step Zero #1)
- ✅ Repo created at `oneKn8/granum`, Apache-2.0, public
- ✅ Python toolchain (uv, Python 3.12), CLI skeleton (`granum doctor`, `granum version`, `granum cycle-all`)
- ✅ GitHub Actions CI — green in 15s
- ✅ Phase 0.4 DONE (2026-05-28): GCP project + billing + APIs + ADC + Vertex Gemini 3.1 Pro Preview verified + Phoenix Cloud space + API key + `smoke_phoenix.py` trace in UI.
- ✅ Phase 1.10a DONE (2026-05-28): `src/granum/tools/phoenix_session.py` — live MCP stdio + REST Bearer auth + `_MCPDictAdapter` for CallToolResult → dict.
- 🟡 Phase 1.10b PENDING: PhoenixClient schema retrofit (see Step Zero #1).
- 🟡 Phase 1.10c PENDING: First live germinal cycle against real Phoenix + Gemini (depends on 1.10b).
- 🔴 Phase 0.5 PENDING: Cloud Run deploy. Now UNBLOCKED (billing is open); needs `infra/deploy.sh` to run and the hosted URL paste into `.env`'s `NEXT_PUBLIC_API_BASE_URL`.

### Phase 1 — Single-cell germinal loop (9/10 done)
All pure-Python, all mockable, all tested:
- ✅ Phase 1.1: Synthetic Aetna cardiac denial generator (10 patterns, 4 tests)
- ✅ Phase 1.2: Gold appeals dataset + loader (12 overturned exemplars, 2 tests)
- ✅ Phase 1.3: **Phoenix MCP+REST client wrapper** (Path B apoptosis: REST tag remove + MCP tag add, 7 tests). `src/granum/tools/phoenix_client.py`
- ✅ Phase 1.4: Negative selection — citation verifier (41-entry valid set, 6 tests)
- ✅ Phase 1.5: Mutation operators (4 kinds, no rewrite, 6 tests)
- ✅ Phase 1.6: LLM-as-judge — 5-axis rubric, median-of-3 sampling, English feedback (3 tests + `data/judge_rubric.md`)
- ✅ Phase 1.7: Tournament engine — concurrent `asyncio.gather`, tie-break by prompt_id (3 tests)
- ✅ Phase 1.8: **GerminalCycle orchestrator** — full single-cell loop with OTel spans (2 integration tests). `src/granum/center/cycle.py`
- ✅ Phase 1.9: Deterministic mutation proposer (5 tests)
- 🔴 Phase 1.10 BLOCKED: Live cycle against real Phoenix Cloud + Vertex Gemini — needs cloud auth

### Phase 2 — Multi-cell + immune memory + antigen drift (4/4 implementation done)
- ✅ Phase 2.1: Cell registry — 5 declared cells, `validated_cells()` filter (6 tests)
- ✅ Phase 2.2-2.4: Data for 4 non-Aetna cells (Terminal B, 4 cells × 4 files each, all citations resolve to valid sets, negative-selection clean)
- ✅ Phase 2.5: **Immune memory** — `memory_cell` tag preservation + 2-extinction reactivation (6 tests). `src/granum/center/immune_memory.py`
- ✅ Phase 2.6: Memory-cell reactivation — folded into 2.5
- ✅ Phase 2.7: **Antigen drift detector** — bag-of-features symmetric difference, 25% threshold (5 tests). `src/granum/center/antigen_drift.py`
- ✅ Phase 2.8: **MultiCellDriver** — runs one cycle per validated cell, integrates memory + drift hooks (3 tests). `src/granum/center/driver.py`
- ✅ Phase 2.9: Cross-cell observability — OTel spans in cycle.py already emit per-cell metadata

### Phase 5 — Frontend + demo polish (Terminal C, COMPLETE)
- ✅ Next.js 15 + Tailwind 4 scaffold in `web/`, build green
- ✅ 5 components: `LineageTree`, `CoEvolutionDualTree`, `FitnessCurve`, `PromptDiff`, `CellSelector`
- ✅ Landing page + per-cell route SSG for all 5 cells
- ✅ Mock data layer at `web/lib/mock-data.ts` (matches `docs/api-contract.md`)
- ✅ `NEXT_PUBLIC_USE_REAL_API` flag wired (Terminal C added in commit `5931687`)
- ✅ Polish pipeline applied sequentially: `baseline-ui` → `fixing-accessibility` → `fixing-motion-performance` → `fixing-metadata` — all four passed
- ✅ `web/DESIGN.md` (Germinal Lab spec, OKLCH palette, banned-defaults checklist)
- ✅ `docs/demo-script.md`, `docs/storyboard.md`, `docs/design-references.md`, `scripts/demo.sh`
- ✅ Browser-verified via Playwright MCP at localhost:3001

### Docs published
- ✅ `docs/PRODUCT.md` — full product narrative
- ✅ `docs/api-contract.md` — JSON contract for FastAPI ↔ Next.js
- ✅ `docs/biology-mapping.md` — Terminal B's immunology essay
- ✅ `docs/cell-curation-methodology.md` — how Terminal B verified citations
- ✅ `docs/demo-script.md`, `docs/storyboard.md` — Terminal C's video plan

---

## What's NOT done — next session scope

### 🟥 BLOCKERS (user-action required, can be done in parallel with code work)

| # | Action | Required for |
|---|---|---|
| B1 | **Open GCP billing on a project**. Options: (a) submit hackathon $100 credit form at https://rapid-agent.devpost.com/resources (1-5 day SLA), (b) reopen billing on `lumentra-ai-485322`, (c) attach billing to `call-agent-485305`. | Phase 0.5 Cloud Run deploy + Phase 1.10 live cycle |
| B2 | **Run `gcloud auth application-default login`** interactively (browser). | Vertex API calls |
| B3 | **Sign up at https://app.phoenix.arize.com**, create project `granum`, generate API key, drop into `/home/oneknight/projects/hackathon/granum/.env`. | Phoenix Cloud operations |

### 🟧 Phase 3 — Red Queen co-evolution (NOT STARTED, Terminal A's main job)

Two-population co-evolution: adversarial payer-agents evolve alongside appeal-writer B-cells. Solves Gemini 2's "LLM-as-judge agreement bias" concern by making appeals defeat an adversary that actively looks for hallucinations.

Tasks per `IMPLEMENTATION_PLAN.md` Phase 3:
1. **3.1** — Payer-agent prompt templates + 5 seeded personas (strict, lenient, formalist, cost-focused, evidence-focused). New file: `src/granum/adversary/payer_agent.py`.
2. **3.2** — Payer-agent ADK definition + tool use
3. **3.3** — Adversarial denial generator (replaces synthetic generator at runtime)
4. **3.4** — Triangular tournament protocol: writer → payer → judge scores defensibility
5. **3.5** — Defensibility scorer (LLM-as-judge variant)
6. **3.6** — Co-evolution driver (alternates appeal-population evolution with payer-population evolution)
7. **3.7** — Anti-degeneracy regularization (cap mutation rate at 15%, reset adversary every 5 generations)
8. **3.8** — Dual-lineage Phoenix queries + writeback
9. **3.9** — Phase 3 integration test (5 co-evolution rounds end-to-end, all mocked)

Failure modes documented in `IMPLEMENTATION_PLAN.md` §Phase 3.

### 🟧 Phase 4 — Cross-cell transfer detection (NOT STARTED)

4 tasks: cell embedding + similarity matrix, transfer trial harness, promotion gate, transfer-edge metadata writeback.

### 🟧 Phase 6 — Submit (NOT STARTED, Terminal C's main job)

5 tasks:
1. Verify license at repo root (already there)
2. Verify hosted URL alive — depends on Phase 0.5 unblock
3. Verify YouTube video public + ≤3 min — needs video recording
4. Fill Devpost form per `docs/submission.md` — **need to write this doc**
5. Submit by 2026-06-10 noon EDT (24h before hard deadline)

---

## Recommended next-session split

### Terminal A (backend) — Phase 3 (Red Queen) + Phase 4 (transfer)
Working dir: `/home/oneknight/projects/hackathon/granum/`
Owns: `src/granum/adversary/`, `src/granum/center/coevolution.py`, `src/granum/center/transfer.py`, related tests.

Start with: read `docs/IMPLEMENTATION_PLAN.md` §Phase 3 §A.3 RedQueen contract. Then dispatch subagents for tasks 3.1 → 3.9 sequentially using `superpowers:subagent-driven-development`.

### Terminal B (data + Phase 3 data) — payer adversary personas + denial pattern expansion
Working dir: `/home/oneknight/projects/hackathon/granum/`
Owns: `data/<cell>/payer_personas.json`, `data/<cell>/adversarial_denial_patterns.json`. Expand each cell's denial pattern bank to 20+ patterns (currently 10 per cell). Curate 5 payer-adversary personas per cell — language style + clinical-policy interpretation rigor.

Boundaries: do NOT touch `src/`, `web/`, `tests/` (Terminal A's lane).

### Terminal C (submission + demo polish) — Phase 6 prep
Working dir: `/home/oneknight/projects/hackathon/granum/`
Owns: `docs/submission.md` (Devpost form text), `videos/`, finalizing `scripts/demo.sh`, recording the 3-min demo video (when Cloud Run deploys), running `web-quality-audit` skill against the deployed site.

When Phase 0.5 unblocks: run `scripts/demo.sh` against the live deploy, capture via Playwright, render with ElevenLabs voiceover (skill installed).

---

## Resume sequence for the FIRST terminal to start

1. `cd /home/oneknight/projects/hackathon/granum/`
2. `git pull --rebase origin main` (always)
3. Read this file + the "Read these first" list above
4. Verify environment:
   ```bash
   git config user.email   # should be: shifatislamsanto764@gmail.com
   gh auth status          # should be: logged in as oneKn8
   env -u PYTHONPATH uv run pytest tests/ -q   # should be: 60 passed
   ```
5. Decide your terminal letter (A, B, or C — match scope above)
6. Update `docs/standup.md` with a fresh entry announcing your start
7. If you are Terminal A: invoke `superpowers:subagent-driven-development` and dispatch Phase 3 Task 3.1
8. If you are Terminal B or C: read your respective STARTUP file (`docs/STARTUP_TERMINAL_B.md` or `docs/STARTUP_TERMINAL_C.md`)

---

## Open questions for next session (lock at start)

1. **Final project name** — currently `Granum` (Latin for grain/kernel, biology nod). Alternatives in `docs/PRODUCT.md` §9: Centra, Affinity, Overturn, Hypermut. Renaming now is a sed-rename across ~30 files and the GitHub repo URL. Decide before Phase 3 starts.
2. **Phase 0.5 retry strategy** — when GCP billing opens, run `infra/deploy.sh`. If credit grant comes back denied, decide: self-fund vs simplify deploy story.
3. **Demo data** — for the video, use synthetic denials (current path) or wait for user-provided real anonymized denials (none provided yet, recommend continuing synthetic).
4. **Submission video voice** — Shifat's voice vs ElevenLabs TTS (skill available). Decide by 2026-06-09.

---

## Headline numbers for the next session's first standup

- Tests: 60/60 passing
- Phoenix MCP audit: complete, Path B locked
- Cells with full data: 5/5 (Aetna + 4 from Terminal B)
- Frontend: complete and Playwright-verified
- API contract: published
- Days to deadline: 15
- Blockers requiring user action: 3 (GCP billing, ADC, Phoenix Cloud key)
