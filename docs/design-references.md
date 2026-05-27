# Granum — Design References

**Aesthetic family:** Cinematic Dark — "Germinal Lab"
**Locked:** 2026-05-27 by Terminal C

The lukewarm middle is the failure state. This pick commits to lab-bench biology over dev-tool dark or corporate-tasteful light. The lineage tree is the primary visual asset (~60% of dashboard real estate); D3 phylogenetic trees pop dramatically on dark backgrounds tuned with biological cell-stain hues, NOT on the saturated supervisor-pattern centroid of neon cyan / terminal green / Tailwind defaults.

---

## Reference set (4 sites)

Pasted, not described. Each chosen for one specific extract.

### 1. Nextstrain — `https://nextstrain.org/`

The closest production reference to what Granum's UI must do: a real-time phylogenetic lineage explorer used by epidemiologists tracking pathogen evolution. Dark UI chrome with a vibrant lineage tree front-and-center. Tip nodes colored by clade; extinct branches greyed.

**Extract:** Tree-as-the-hero layout. The lineage IS the product; no dashboard widget grid around it. We borrow this exactly: landing page is the tree.

### 2. Observable HQ — D3 hierarchical tree examples — `https://observablehq.com/@d3/tree`

The canonical idiom for `d3.hierarchy()` + zoom + collapsible nodes. Editorial-density data UI: code, tree, prose, and explanatory captions all coexist on one canvas.

**Extract:** Inline annotation + tree pattern. Hover on a branch shows a side-panel with the prompt diff. Not a tooltip — a persistent inspector.

### 3. every.to — `https://every.to/`

Dark-mode editorial typography. Serif headlines on near-black, with restrained accents. Proves a dark editorial product can feel literary rather than terminal-utility.

**Extract:** IBM Plex Serif for hero + prose. Generous line-height. Wide measure on body copy. No sans-serif everywhere.

### 4. Cell Press journals — `https://www.cell.com/`

Academic biology visual language. Microscopy imagery uses eosin-blue, hematoxylin-amber, methyl-violet magenta. This is the source for the OKLCH palette below.

**Extract:** The cell-stain palette. Color carries semantic biology meaning (alive / champion / mutant / tombstoned), not decoration.

---

## Anti-references (what we are NOT)

- **Mission-Control / War Room dashboards** — every other Arize-track entry (mender, agent-sre, aegis, flightcheck). KPI tile grid + log stream + status indicators. The supervisor-pattern centroid's visual identity. Granum is not a battle station.
- **Streamlit / FastAPI-minimal-HTML chrome** — utility-grade defaults; signals "I didn't design this." Aegis-1, axon both fall here.
- **Tailwind CDN with default `blue-500`/`cyan-400` accents** — agent-sre uses this; it is the AI-default fingerprint.
- **Neon cyan / terminal green dark mode** — Cyberpunk dev-tool aesthetic. We are biology, not hacker movie.
- **Centered hero + 2 CTAs / 3-card feature grid / Stats row (10K+/99%/24/7) / "Trusted by" strip / Pill buttons with gradient bg / Sticky nav with backdrop-blur** — Claude's reach-for defaults. All banned in `web/DESIGN.md`.

---

## Why this commits hard to one extreme

Per the Masterpiece Playbook: pick an extreme; the lukewarm middle is the failure state. Cinematic Dark — Germinal Lab — is contrastive against every published competitor in this track AND against the medical-software cliché of clinical-clean white. It earns its biology metaphor instead of decorating with it.
