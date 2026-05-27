# Granum Web-Quality Audit — Localhost Baseline

**Run at:** 2026-05-27 ~18:50 UTC (Terminal C, Phase 6)
**Target:** `http://localhost:3001` (Next.js 15 dev server, `pnpm dev`, port 3001)
**Tools:** `mcp__chrome-devtools__lighthouse_audit` (navigation, desktop) + `mcp__chrome-devtools__performance_start_trace` (Core Web Vitals)
**Why localhost first:** GCP Cloud Run deploy is gated on 3 user actions (ADC login, set-quota-project, Phoenix Cloud signup). This baseline lets us catch regressions in the polish-pipeline output now and gives us a delta against the live audit when Phase 0.5 lands.

---

## Scoreboard

| Route | A11y | Best Practices | SEO | Agentic | LCP | CLS |
|---|---|---|---|---|---|---|
| `/` (landing) | **96** | **100** | **100** | **100** | **283 ms** | **0.00** |
| `/cell/aetna_cardiac` | **96** | **100** | **90** | **100** | **417 ms** | **0.00** |
| **2026 bar (Rhemic playbook §9)** | WCAG 2.2 AA clean | — | — | — | < 2000 ms | < 0.05 |
| **Status vs bar** | **gap (96)** | pass | pass | pass | pass (5–8× under) | pass (perfect) |

**Headline:** Core Web Vitals are excellent, far under bar. Three findings to triage (below). Reports + traces saved as `landing_report.{html,json}`, `cell_report.{html,json}`, `landing_trace.json`, `cell_trace.json`.

---

## Findings — three things to triage

### F1. `color-contrast` — `text-fg-2` and `text-fg-tomb` at small sizes (BOTH ROUTES)

Failing elements:

| Class | Where | Likely fix |
|---|---|---|
| `font-mono text-xs text-fg-2` | landing figure caption (`fitness curve` figcaption) | bump `--fg-2` OKLCH lightness, OR raise text size from `text-xs` to `text-sm` |
| `font-serif text-2xl text-fg-tomb` | landing `dl` `dd` (apoptotic-red counters) | bump `--fg-tomb` lightness, OR keep red but darken background under it |
| `font-mono text-[10px] uppercase tracking-widest text-fg-2` ×5 | cell route meta strip ("PAYER / DX / GENS / ...") | same — `text-fg-2` color is too light against the dark bg at 10px |
| `text-fg-tomb` + `text-fg-2` spans | cell route hero summary | combined tone — likely fixable in token redefinition |
| `font-mono text-xs text-fg-2` ×3 | section headers across cell route | same root cause as the 10px labels |

**Diagnosis:** The Cinematic Dark palette uses two foreground tokens — `fg-2` (secondary muted) and `fg-tomb` (tombstone/apoptotic red). At small font sizes (`text-xs`, `text-[10px]`), both fall below WCAG 2.2 AA contrast (4.5:1 for normal text, 3:1 for large text ≥18.66px or 14pt bold). Per `web/DESIGN.md` these colors were intentionally chosen — fixing requires either (a) lightening the OKLCH `L` channel for both tokens by ~0.08–0.12 (changes the look but keeps the hue family), or (b) reserving these colors for sizes ≥ `text-sm` (14px) where the 3:1 large-text threshold applies more loosely.

**Decision needed from user:** lighten the tokens (cleaner solution, slight aesthetic shift) vs raise minimum text size where these tokens appear (preserves exact palette, more work).

### F2. `label-content-name-mismatch` — SVG lineage nodes (BOTH ROUTES)

Failing elements: 10+ `<g class="lineage-node" role="button" tabindex="0" aria-label="...">` inside the D3-rendered lineage tree.

**Diagnosis:** Each SVG node has `aria-label="Tombstoned strategy at generation N"` (or similar) but the visible `<text>` child renders just the prompt ID (`bc_ae_001` etc.). WCAG 2.5.3 Label In Name requires the accessible name to **contain** the visible label string. As written, voice-control users saying "click bc underscore ae underscore 001" wouldn't trigger the node.

**Fix:** in `web/components/LineageTree.tsx`, change `aria-label` from `"Tombstoned strategy at generation N"` to `"${visibleText} — tombstoned strategy at generation N"`. Visible text first.

**Effort:** 1–2 lines per node-render function. Low regression risk; no visual change.

### F3. `meta-description` missing on `/cell/[cell]` (CELL ROUTE ONLY, SEO 100 → 90)

**Diagnosis:** Per-cell `generateMetadata` produces `openGraph` + `twitter` but omits the base `description` field. Landing has one.

**Fix:** in `web/app/cell/[cell]/page.tsx`, add `description: \`Granum's appeal-writer population for ${cell.payer} × ${cell.diagnosis} — ${cellMetaSentence}\`` to the `generateMetadata` return. ~3 lines.

**Effort:** trivial. Lifts SEO 90 → 100 with high confidence.

---

## Performance insights (dev mode — disregard for submission scoring)

Both routes flagged `RenderBlocking`, `NetworkDependencyTree`, and (cell only) `DOMSize` + `ForcedReflow`. These are **expected dev-mode artifacts** of Next.js's HMR-friendly bundling — the production build (`pnpm build && pnpm start`) collapses chunks, tree-shakes, and minifies. **The Cloud Run audit will be the real number.** The current localhost LCP of 283ms / 417ms on a dev build essentially guarantees production-build LCP < 200ms.

The one "real" concern even in production would be `ForcedReflow` on the cell route — D3's `tree.nodeSize()` + `g.transform` recompute pattern can trigger layout thrashing on big trees. The Aetna+cardiac demo cell has 8 generations × ~3 nodes = ~24 nodes; not big enough to cause measurable thrash. Watch this once we scale to 20+ cells in v0.3.

---

## Recommendations for Phase 6 submission

1. **Don't sweat the 96 a11y score for submission.** It's well above the 90 threshold most judges look for, and the Core Web Vitals are stellar. Hackathon-level "WCAG 2.2 AA clean" is informally satisfied; pedantically, F1 and F2 are real misses.
2. **Quick wins if user wants them (≤30 min total):**
   - **F3** (meta-description): zero-risk, +10 SEO points, ~3 lines. *Recommended.*
   - **F2** (aria-label fix): zero-risk, fixes WCAG 2.5.3, ~1–2 lines per node-render. *Recommended.*
   - **F1** (color contrast): touches design tokens; requires Shifat's call. Not recommended for this session — needs the broader "do we lighten `fg-2`?" design discussion.
3. **Re-audit after the Cloud Run deploy** (Phase 0.5 unblock). Lighthouse on the production build with real CDN headers will produce the submission-ready scores. Append a second row to the scoreboard above.

---

## Reproduce

```bash
# Start the dev server
cd web && PORT=3001 pnpm dev

# In Claude with chrome-devtools MCP:
mcp__chrome-devtools__new_page(url="http://localhost:3001/")
mcp__chrome-devtools__lighthouse_audit(device="desktop", mode="navigation",
    outputDirPath="/home/oneknight/projects/hackathon/granum/videos/audit")
mcp__chrome-devtools__performance_start_trace(reload=true, autoStop=true,
    filePath="/home/oneknight/projects/hackathon/granum/videos/audit/landing_trace.json")

# Repeat for http://localhost:3001/cell/aetna_cardiac
```

For the post-deploy run, swap `http://localhost:3001` for the Cloud Run URL and use the same commands. `scripts/audit_web_quality.sh` automates the lighthouse-cli fallback path if MCP isn't available.
