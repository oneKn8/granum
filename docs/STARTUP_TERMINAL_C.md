# Terminal C startup prompt — Frontend + Demo Materials

Copy-paste the block below into a fresh Claude Code terminal:

---

You are Terminal C in a 3-terminal parallel build for the Google Cloud Rapid Agent Hackathon (Arize Phoenix track), deadline 2026-06-11. The project is Granum — an evolutionary appeal-writer for denied medical care. Three Claude Code terminals are running concurrently against the same repo.

**FIRST: read these in order, in full:**
1. `/home/oneknight/projects/hackathon/research/draft-project-docs/COORDINATION.md` — your scope + boundaries
2. `/home/oneknight/projects/hackathon/research/draft-project-docs/IMPLEMENTATION_PLAN.md` — search for "Phase 5" and read that section
3. `/home/oneknight/projects/hackathon/research/draft-project-docs/README.md` and `PRODUCT.md` — design vocabulary
4. `/home/oneknight/projects/hackathon/research/competitor-readmes/*.md` — read all 6, identify design anti-patterns
5. `/home/oneknight/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-polish-pipeline.md` — mandatory polish pipeline
6. `/home/oneknight/.claude/projects/-home-oneknight-projects-hackathon/memory/user-engineering-bar.md` — the bar

**Your scope:** Next.js frontend + demo materials. NO Python, NO backend.

**Tasks:**

1. **Wait for repo to exist.** Poll `ls /home/oneknight/projects/hackathon/granum/` every 60s until present.

2. **Scaffold Next.js 15 + TypeScript + Tailwind in `web/`** subdirectory:
   - App Router
   - Tailwind 4
   - shadcn/ui only if you need it (lean default — no shadcn/ui unless justified)
   - D3 for the lineage tree (`d3-hierarchy`, `d3-zoom`)
   - Recharts for fitness curves
   - `web/lib/mock-data.ts` — sample data matching the eventual API contract (Terminal A publishes contract at `docs/api-contract.md` by Phase 3)

3. **Build core components against mock data:**
   - `web/components/LineageTree.tsx` — phylogenetic tree of B-cell strategies. Survivors branch. Tombstoned nodes greyed out with strikethrough lineage. Hover shows prompt body diff vs parent.
   - `web/components/CoEvolutionDualTree.tsx` — two LineageTrees side by side (appeal-writer population + payer-adversary population).
   - `web/components/FitnessCurve.tsx` — per-cell fitness over generations (Recharts line chart).
   - `web/components/PromptDiff.tsx` — side-by-side parent → mutant diff with citation/paragraph changes highlighted.
   - `web/components/CellSelector.tsx` — switch between 5 (payer × diagnosis) cells.
   - `web/app/page.tsx` — landing page with hero + lineage tree front-and-center.
   - `web/app/cell/[cell]/page.tsx` — per-cell dashboard.

4. **Apply polish pipeline SEQUENTIALLY** (not parallel) on `web/`:
   - Invoke `baseline-ui` skill — validate animation durations, typography scale, anti-patterns
   - Invoke `fixing-accessibility` skill — WCAG 2.2 AA, ARIA, keyboard nav
   - Invoke `fixing-motion-performance` skill — compositor properties, no layout thrashing
   - Invoke `fixing-metadata` skill — page titles, OG tags, JSON-LD, canonical URLs
   - For each: read the skill, follow its checklist, mark each item complete

5. **Design anti-patterns to AVOID** (Claude reaches for these unprompted):
   - Inter / Space Grotesk fonts → pick something else (Söhne, IBM Plex Serif, JetBrains Mono for monospace)
   - `bg-gray-50` / purple-blue gradients on white
   - Centered hero with 2 CTAs
   - 3-card feature grid with lucide icons
   - Pill buttons with gradient bg
   - "Trusted by" logo strip
   - Stats row (10K+/99%/24/7)
   - Sticky nav with backdrop-blur

6. **Aesthetic family:** Cinematic Dark OR Editorial Minimalism (pick one and commit). The germinal center metaphor wants either rich biological imagery (Cinematic Dark with OKLCH-tuned cell-stain blues/violets) or stark academic clarity (Editorial Minimalism with serif headlines + dense data tables). Pick one extreme. The lukewarm middle is failure.

7. **`docs/demo-script.md`** — 3-min storyboard, 20-sec beats:
   - 0:00-0:20 Patient denial story + AMA stats
   - 0:20-1:00 Inject denial, 3 mutants compete, winner emerges, losers tombstoned, lineage tree updates live
   - 1:00-1:30 Winning appeal shown — citations highlighted
   - 1:30-2:00 6 weeks fast-forward, lineage tree branches, fitness curve climbs
   - 2:00-2:30 Prompt diff Gen 1 vs Gen 8
   - 2:30-3:00 Closer — overturn rate climbed, lineage as system of record

8. **`docs/storyboard.md`** — frame-by-frame visual storyboard with screenshot/sketch placeholders.

9. **`scripts/demo.sh`** — orchestrator that:
   - Runs `granum doctor`
   - Runs `granum seed`
   - Runs 5-8 cycles with deterministic seeds
   - Starts `web` server
   - Opens browser to `/cell/aetna_cardiac`
   - Captures via `mcp__plugin_playwright_playwright__browser_*` for the recording
   - Configurable `DEMO_PACE`, `DEMO_FRESH=1` to reset state

**Boundaries (DO NOT TOUCH):**
- Any `.py` file
- Any `data/**` file
- `pyproject.toml`
- `LICENSE`
- `infra/**`

**Status reporting:** Every 30-60 min, append to `/home/oneknight/projects/hackathon/granum/docs/standup.md`:

```markdown
## [Terminal C] — 2026-05-MM HH:MM
- DONE: <what>
- IN PROGRESS: <what>
- BLOCKED: <why>
- NEXT: <what>
```

**Commit policy:** Frequent small commits prefixed `[C] feat(web): ...` or `[C] docs: ...`. Pull before push.

**Process discipline:** Read the 6 files at top BEFORE writing any code. Spend 20 min on design discovery (font, color, aesthetic family lock) before scaffolding. Pick one extreme aesthetic. Reference 2-4 actual screenshots from Awwwards/godly.website/SiteInspire — paste links into a `docs/design-references.md`.

Begin by reading the 6 files. Then wait for repo. Then scaffold Next.js.
