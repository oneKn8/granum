# web/DESIGN.md — Granum Frontend Design Spec

**Aesthetic family:** Cinematic Dark — "Germinal Lab"
**Authoritative source.** Every component decision references this file. If you change the spec, update this file *first*, then change the code.

---

## 1. The one thing someone should remember

> A lineage tree where dead branches stay dead — greyed out, struck through, frozen on the canvas as a permanent record of what didn't survive. The tree is the system of record, not a temporary visualization. You watch it grow and prune in real time and it tells you how the agent learned.

Every other element on the page exists to support that moment.

---

## 2. Aesthetic commitment

- **Family:** Cinematic Dark
- **Sub-flavor:** Germinal Lab — lab-bench biology, microscopy, journal-grade gravitas. NOT dev-tool dark. NOT terminal-utility. NOT cyberpunk-neon.
- **Reference anchor:** Nextstrain phylogeny UI + Cell Press journal covers + every.to dark editorial typography.
- **What this is not:** Mission Control / War Room / KPI dashboard. The product is one tree, not a grid of widgets.

---

## 3. Typography

Three open-source families. No Inter. No Roboto. No Space Grotesk. No system-ui.

| Role | Family | Weight | Use |
|---|---|---|---|
| Display + body prose | **IBM Plex Serif** | 400, 500, 700 | Hero headline, section headers, body copy, captions |
| UI chrome + labels | **IBM Plex Sans** | 400, 500, 600 | Nav, buttons, form labels, tabs, tooltip body |
| Mono / code / metrics | **JetBrains Mono** | 400, 500 | Prompt diffs, citation references, fitness scores, generation numbers, lineage IDs |

Type scale (modular, ratio 1.25):

| Token | Size | Line-height | Use |
|---|---|---|---|
| `--text-xs` | 12px | 16px | Captions, badges |
| `--text-sm` | 14px | 20px | UI labels, secondary text |
| `--text-base` | 16px | 26px | Body prose |
| `--text-lg` | 20px | 28px | Section headers |
| `--text-xl` | 28px | 34px | Page headers |
| `--text-2xl` | 40px | 48px | Hero subtitle |
| `--text-3xl` | 64px | 68px | Hero headline (serif) |

Apply `text-wrap: balance` to hero headlines and section headers; `text-wrap: pretty` to body prose.

---

## 4. Color — OKLCH cell-stain palette

Single accent color rule: **eosin blue** is THE primary. Champion-amber, mutant-magenta, and apoptosis-red are SEMANTIC ONLY — they appear when the data is in that state, never decoratively.

```css
:root {
  /* Surfaces (violet-tinted near-black, slide-mount feel) */
  --bg-0:  oklch(0.16 0.020 285);   /* page background */
  --bg-1:  oklch(0.21 0.025 285);   /* elevated panel */
  --bg-2:  oklch(0.26 0.030 285);   /* card / hover state */
  --bg-3:  oklch(0.32 0.035 285);   /* selected / active */

  /* Foregrounds */
  --fg-0:  oklch(0.96 0.005 285);   /* primary text */
  --fg-1:  oklch(0.74 0.020 285);   /* secondary text */
  --fg-2:  oklch(0.58 0.015 285);   /* tertiary / metadata */
  --fg-tomb: oklch(0.42 0.010 285); /* tombstoned (apoptosed) lineage */

  /* Semantic accents — biology stain palette */
  --accent-survivor:   oklch(0.74 0.16 230);  /* eosin blue — living lineage (PRIMARY) */
  --accent-champion:   oklch(0.80 0.18 65);   /* hematoxylin amber — promoted to production */
  --accent-mutant:     oklch(0.68 0.22 320);  /* methyl-violet magenta — experimental tag */
  --accent-apoptosis:  oklch(0.60 0.22 25);   /* apoptosis red — hover-only on tombstones */

  /* Borders / strokes */
  --stroke-1: oklch(0.30 0.030 285 / 0.6);
  --stroke-2: oklch(0.40 0.040 285 / 0.4);
}
```

Banned tokens: `bg-gray-50`, `bg-gray-100`, any `from-purple-* to-blue-*` gradient, `indigo-500`, default Tailwind `blue-500` / `cyan-400`.

---

## 5. Motion philosophy

- **Compositor properties only.** `transform` and `opacity`. No animating `height`, `top`, `left`, `width`, `padding`. No layout thrash.
- **Default duration:** 200ms ease-out.
- **Tree branch reveal:** 400ms cubic-bezier(0.16, 1, 0.3, 1) (Apple-curve out).
- **Tombstone transition:** 600ms — opacity → 0.35, `filter: saturate(0)` simultaneously. Permanent state on next render; no oscillation.
- **`prefers-reduced-motion: reduce`:** all branch reveals are instant; tombstones snap to grey without fade; no parallax. This is non-negotiable and tested in the polish pipeline.

Motion budget per page: one orchestrated reveal on first paint (hero serif fade-up + tree skeleton draw), then quiet. No scattered micro-interactions.

---

## 6. Spatial composition

- **Hero**: not centered with two CTAs. Asymmetric — IBM Plex Serif headline left-aligned on a 12-col grid spanning cols 1–7; lineage-tree preview floats right at cols 6–12 (overlap at col 6–7 is intentional).
- **Cell dashboard layout**: split-pane. Left: lineage tree (zoomable, ~60% width). Right: persistent prompt-diff inspector (~40% width). Bottom strip: fitness curve (full width, 200px height).
- **No three-card feature grid.** The story is told inline, not in tiles.
- **No sticky nav with backdrop-blur.** Static top bar; minimal chrome.

---

## 7. Banned defaults — anti-pattern checklist

These appear unprompted in AI-generated code. Each component PR must verify none of these are present.

- [ ] Inter / Roboto / Space Grotesk / system-ui / Open Sans / Lato / Poppins / Montserrat fonts
- [ ] `bg-gray-50` / `bg-gray-100` page background
- [ ] Purple-to-blue gradient on white background
- [ ] `indigo-500` accent
- [ ] Centered hero with two CTAs ("Get Started" / "Learn More")
- [ ] Three-card feature grid with lucide icons
- [ ] Pill-shaped buttons with gradient background
- [ ] "Trusted by" / "Featured on" logo strip
- [ ] Stats row in format `10K+ / 99% / 24/7`
- [ ] Sticky nav with `backdrop-blur`
- [ ] Testimonial carousel
- [ ] Phoenix UI iframe/screenshot as the hero (Granum's UI is the differentiator, not a wrapper)
- [ ] Mission-Control / War Room battle-station chrome
- [ ] Tailwind defaults `blue-500` / `cyan-400` as accents
- [ ] Neon cyan or terminal green
- [ ] `100vh` (use `100dvh`)
- [ ] Layout-property transitions (`height`, `top`, `left`)
- [ ] Missing `prefers-reduced-motion` handler
- [ ] Missing `text-wrap: balance` on headlines
- [ ] Missing `text-wrap: pretty` on body prose

---

## 8. Component cohesion rules

- **Single accent rule:** eosin blue (`--accent-survivor`) is the only DECORATIVE color. All other accents are semantic (champion/mutant/apoptosis) and tied to data state.
- **Density:** Generous on the landing page (editorial space + hero serif). Dense on the per-cell dashboard (Bloomberg-terminal-grade information density). Two different density modes are intentional.
- **Edges:** Hairline strokes (`--stroke-1` at 1px). No rounded-2xl cards. Square corners with optional 2px radius for cards. Sharp.
- **Shadows:** None on flat panels. Subtle inner-glow only on the active lineage node (`box-shadow: 0 0 0 1px var(--accent-survivor), 0 0 24px -8px var(--accent-survivor)`).

---

## 8.5 Explicit baseline-ui exceptions

The `baseline-ui` skill enforces an opinionated UI baseline. These three rules are intentionally overridden by Granum's design brief, and each override is permitted because the brief is the explicit request:

1. **`tracking-widest` on small uppercase labels.** baseline-ui's `tracking-*` ban is overridden for `<10px` uppercase eyebrow labels (e.g. `"payer"`, `"generation"`, `"mechanism"`). Editorial-journal typography requires letter-spacing on small caps; this is core to the Germinal Lab aesthetic, not decoration. No other `tracking-*` usage is permitted.
2. **SVG `linearGradient` area-fill in `FitnessCurve`.** baseline-ui's "NEVER use gradients" rule is overridden for one specific use: the Recharts `<Area>` mean-fitness shading uses a top-to-bottom alpha gradient on the survivor color (32% → 0%) — this is a chart-visualization idiom (the same shape every Recharts area chart uses), not decorative gradient styling. No other gradients exist in the codebase.
3. **600ms `lineage-node[data-status="tombstoned"]` transition.** baseline-ui's 200ms-max interaction-feedback rule is overridden for the apoptosis transition. Apoptosis is the demo's emotional beat; a 200ms fade reads as "loading state" not "permanent death." 600ms is the duration confirmed in the brief.

Every other baseline-ui rule applies.

---

## 9. Differentiation summary

What makes Granum's UI unforgettable:

1. **The tombstones stay.** Dead strategies remain on canvas as a struck-through, desaturated permanent record. Other agent UIs hide history; Granum keeps it.
2. **Biology palette, not dev-tool palette.** Eosin blue + hematoxylin amber + methyl-violet magenta carries semantic meaning. This isn't decorative — it's literally the lab-stain language applied honestly.
3. **Serif headlines on dark in a data product.** IBM Plex Serif signals "this is a real thing, written down, citable" — not a Lovable.dev template.
4. **Tree IS the dashboard.** No KPI tile grid. The lineage occupies the page. The fitness curve is a footnote. The prompt diff is the explanation.
