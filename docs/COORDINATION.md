# Granum Multi-Terminal Coordination

**Created:** 2026-05-27
**Purpose:** Prevent stepping on each other across 3 parallel Claude Code sessions.

---

## Terminal split

### Terminal A — Backend + Phoenix integration (OWNS Python code, infra, agent)

Working directory: `/home/oneknight/projects/hackathon/granum/` (created during Phase 0 Task 0.1)

Owns:
- `src/granum/**` — all Python code
- `tests/**`
- `infra/**`
- `pyproject.toml`, `.env.example`, `.gitignore`
- `.github/workflows/**`
- `LICENSE`, `README.md` (root) — coordinate before edit
- `scripts/**`
- Phoenix MCP audit + integration
- All Phase 0, 1, 2 (impl), 3, 4 (impl) tasks

Pre-flight Task A (Phoenix MCP audit) runs here first.

### Terminal B — Data + content curation (OWNS data files, NO Python)

Working directory: `/home/oneknight/projects/hackathon/granum/` (after Terminal A creates it — wait 10 min)

Owns:
- `data/aetna_cardiac/*.jsonl` and `*.json` (Terminal A creates `data/aetna_cardiac/denial_templates.json` + `data/aetna_cardiac/valid_citations.json` + `data/aetna_cardiac/gold_appeals.jsonl` as part of Phase 1)
- `data/united_oncology/**` (NEW — Terminal B owns from scratch)
- `data/anthem_mental_health/**` (NEW)
- `data/cigna_ortho/**` (NEW)
- `data/humana_endocrinology/**` (NEW)
- `data/judge_rubric.md` (NEW — Terminal B owns)
- `data/judge_rubric_variants/*.md` (per-cell judge rubric specializations)
- `docs/biology-mapping.md` (NEW — Terminal B writes the immunology → prompts essay)
- `docs/cell-curation-methodology.md`

Does NOT touch:
- Python code
- Phoenix MCP integration
- Frontend

Wait condition: Terminal A confirms `data/aetna_cardiac/denial_templates.json` exists (signals Phase 1 Task 1.1 done) before Terminal B begins, so Terminal B can match the same JSON schema.

### Terminal C — Frontend + demo materials (OWNS Next.js, demo, video)

Working directory: `/home/oneknight/projects/hackathon/granum/web/` (Terminal C creates this subdir from scratch — no waiting on Terminal A)

Owns:
- `web/**` — entire Next.js app
- `web/package.json`, `web/tsconfig.json`, `web/next.config.ts`, `web/tailwind.config.ts`
- `web/app/**`, `web/components/**`, `web/lib/**`
- `web/public/**`
- `docs/demo-script.md` (NEW)
- `docs/storyboard.md` (NEW)
- `scripts/demo.sh` (NEW — Terminal C writes the screen-recording orchestrator)
- `videos/**` (NEW — voiceover + final video)
- Polish pipeline skill invocations: `baseline-ui`, `fixing-accessibility`, `fixing-motion-performance`, `fixing-metadata` (all on web/ only)

Does NOT touch:
- Python code outside `scripts/demo.sh` (which only calls existing CLI commands)
- Backend
- `data/**` (except reading mock data Terminal C generates in `web/lib/mock-data.ts`)

Uses mock data from `web/lib/mock-data.ts` until Phase 5 integration day; Terminal A publishes the JSON-API contract before then in `docs/api-contract.md`.

---

## Shared files — coordinate before editing

These files are touched by multiple terminals. ALWAYS pull latest + check `COORDINATION.md` "Last edits" log below before editing.

| File | Owner default | When others edit |
|---|---|---|
| `README.md` (root) | A | C may add demo-link section at Phase 5 |
| `docs/PRODUCT.md` | A | B may add "biology-mapping" cross-link |
| `docs/architecture.md` | A | C may add frontend-architecture appendix |
| `docs/submission.md` | A | B + C provide content for the form's text fields |
| `LICENSE` | A | NEVER touch after Phase 0 |
| `pyproject.toml` | A | NEVER touch from B or C |
| `package.json` | C | NEVER touch from A or B |

---

## Communication protocol

Every terminal writes a status update to `docs/standup.md` once per work block (every 30-60 min of agent work). Format:

```markdown
## [Terminal X] — 2026-05-MM HH:MM
- DONE: <task ids>
- IN PROGRESS: <task id>
- BLOCKED: <task id> — <why>
- NEXT: <task id>
```

Before starting a task, terminal reads `docs/standup.md` to see if anyone else is on it.

---

## Last edits log (append only)

| Time | Terminal | File | Action |
|---|---|---|---|
| 2026-05-27 11:30 | A | (init) | COORDINATION.md created |

---

## Branch / commit policy

- All terminals work on `main` directly. Frequent small commits with terminal prefix in message: `[A] feat: ...`, `[B] data: ...`, `[C] feat(web): ...`.
- Before pushing: `git pull --rebase origin main` always.
- If conflict on file you don't own: stop, ping in `docs/standup.md`, wait for owner.
- One push at a time per terminal. Pull immediately after.

---

## What each terminal does ON STARTUP

### Terminal A (this one)
1. Read this file
2. Read `IMPLEMENTATION_PLAN.md`
3. Run Pre-flight Task A (Phoenix MCP audit)
4. Then Phase 0 → Phase 1 → Phase 2 (impl) → Phase 3 → Phase 4 (impl) sequentially

### Terminal B
1. Read `/home/oneknight/projects/hackathon/research/draft-project-docs/COORDINATION.md` (this file)
2. Read `/home/oneknight/projects/hackathon/research/draft-project-docs/IMPLEMENTATION_PLAN.md` Phase 2 §
3. Wait for repo to exist (poll `ls /home/oneknight/projects/hackathon/granum/` until present)
4. Wait for `data/aetna_cardiac/denial_templates.json` to exist (signals schema is set)
5. Then curate the 4 new cells in parallel, write JSONL files in matching schema

### Terminal C
1. Read `/home/oneknight/projects/hackathon/research/draft-project-docs/COORDINATION.md` (this file)
2. Read `/home/oneknight/projects/hackathon/research/draft-project-docs/IMPLEMENTATION_PLAN.md` Phase 5 §
3. Wait for repo to exist (poll `ls /home/oneknight/projects/hackathon/granum/` until present)
4. Read `/home/oneknight/projects/hackathon/research/competitor-readmes/*` for design anti-patterns
5. Scaffold Next.js in `web/` subdir with mock data
6. Build lineage tree, fitness curve, prompt diff components
7. Run polish pipeline skills sequentially
8. Write demo script + storyboard
