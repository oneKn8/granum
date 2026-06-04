# web/DESIGN.md — Granum Frontend Design Spec

**Aesthetic family:** Warm Editorial × Data-Dense — **"Agar Lab"** (light brightfield microscopy / Cell-journal figure).
**Authoritative source.** Every component references this file. Change the spec here *first*, then the code.

> Reconciliation note (2026-06-04): this replaces the previous "Cinematic Dark — Germinal Lab" spec.
> The product is now **LIGHT**: warm bone/agar paper, chlorophyll-green lineage, brightfield not darkfield.

---

## 1. The one thing someone should remember

> A living lineage **climbs**. A naive seed strategy enters at the bottom-left at fitness 0.40; across ten
> generations it mutates, most variants die and stay on the page as hollow struck cells, and one bright
> survival spine threads up-and-to-the-right to a glowing gold champion at 0.98. You can watch it grow on
> camera. The tree is the system of record — selection made visible.

Fitness is **vertical height**. Time is **horizontal**. The spine literally goes up and to the right. Every
other element supports that single read.

---

## 2. Aesthetic commitment

- **Family:** Warm Editorial × Data-Dense. Light ground.
- **Metaphor:** *Agar under lab light.* A brightfield microscopy slide / a Cell or Nature journal figure.
  Granum = the chlorophyll-stacked **granum** inside a chloroplast + Latin for **grain/seed** → germination.
- **Reference anchors:** Nextstrain/Auspice (one color encoding binds tree+metrics+detail), Grow by Ginkgo
  (warm off-white + muted green, science-as-wonder), 23andMe (one living green = "a sign of life", AA baked in),
  Quanta/Cell journal figures (editorial serif gravitas, hairline rules, generous air).
- **What this is NOT:** dark dashboard, SaaS blue-on-white, purple gradients, KPI-tile mission-control,
  sterile medical-billing portal. The lineage tree is the hero — never a stock DNA-helix render.

---

## 3. Typography — "Germinal" stack

Three roles map to the three pillars of the product: **organism / human / instrument.** No Inter, Roboto,
Open Sans, Lato, Poppins, Montserrat, system-ui, **Space Grotesk**.

| Role | Family | Axes / weights | Use |
|---|---|---|---|
| **Display** | **Fraunces** (variable) | `opsz` 9–144, `wght`, `SOFT`, `WONK` | Hero + section headlines, the human-stakes copy. An "old-style" soft-serif with ball terminals — literally an organism with growth knobs. |
| **Body** | **Hanken Grotesk** (variable) | `wght` 400–700 | Paragraphs, captions, UI labels. Warm humanist grotesque; dodges Inter's clinic. |
| **Mono** | **IBM Plex Mono** | 400, 500, 600 | Fitness scores, generation counts, lineage IDs, diffs — *instrument readout*, `tabular-nums` always. |

**Expressive Fraunces settings:** hero `opsz ~120, wght ~360, SOFT ~50` (organic, soft); section heads
`opsz ~72, wght ~480, SOFT 0, WONK 0` (authority). Body Hanken 16px / 1.6, weight 400.

Type scale (modular ~1.28):

| Token | Size | Line-height | Use |
|---|---|---|---|
| `--text-xs` | 12px | 16px | eyebrow labels, badges |
| `--text-sm` | 14px | 21px | UI labels, secondary |
| `--text-base` | 16.5px | 27px | body prose |
| `--text-lg` | 21px | 29px | section subheads |
| `--text-xl` | 30px | 36px | page headers |
| `--text-2xl` | 44px | 50px | hero subtitle |
| `--text-3xl` | 68px | 70px | hero headline (Fraunces) |

`text-wrap: balance` on headlines; `text-wrap: pretty` on body.

---

## 4. Color — light OKLCH, one-knob "agar" system

The ground is **agar under lab light**: warm bone/straw, never `#fff`, never `gray-50`. Ink is warm near-black.
The primary is **chlorophyll/granum green** (`--brand-hue 150`). Secondary is **seed amber** (`--seed-hue 75`).
Neutrals are **tinted toward warm** (hue 95–110, never `C 0`) — that is what makes it feel alive, not sterile.

One color does narrative work (Nextstrain rule): the **fitness/status ramp** — green (alive) → gold (champion) —
reused on the tree, the fitness curve, and the stat readouts so a champion reads the same hue everywhere.

```css
--brand-hue: 150;   /* chlorophyll/granum */    --seed-hue: 75;   /* amber */

/* Paper / agar / bone — warm, never white, never gray-50 */
--paper:     oklch(0.985 0.012 95);   /* page ground */
--agar:      oklch(0.970 0.018 95);   /* deeper panel / inset */
--surface:   oklch(0.994 0.008 95);   /* raised card */
--well:      oklch(0.955 0.020 92);   /* sunken well / code block */

/* Ink — warm near-black, never #000 */
--ink:        oklch(0.205 0.020 95);  /* ~16:1 on paper, AAA */
--ink-muted:  oklch(0.470 0.022 110); /* secondary, ~5.6:1 AA */
--ink-subtle: oklch(0.505 0.020 110); /* meta / captions, AA at small sizes */

/* Primary — chlorophyll green (text-safe at L 0.52) */
--primary:        oklch(0.520 0.130 150);
--primary-strong: oklch(0.430 0.120 150);
--primary-tint:   oklch(0.945 0.045 150);
--on-primary:     oklch(0.985 0.012 95);

/* Lineage status ramp (green → gold) + stains */
--alive:      oklch(0.560 0.135 152);  /* surviving production lineage */
--alive-tint: oklch(0.940 0.050 152);
--mutant:     oklch(0.560 0.130 330);  /* experimental tag — methyl-violet stain, SEMANTIC ONLY */
--champion:   oklch(0.715 0.150 82);   /* ripening gold — the matured winner */
--champion-ink: oklch(0.470 0.110 78); /* gold text on paper, AA */
--dead:       oklch(0.610 0.012 110);  /* apoptosed hollow-ring stroke (grey, reads on light) */
--dead-ink:   oklch(0.500 0.020 110);  /* tombstone label */

/* Seed amber (germination accent, distinct from champion gold) */
--seed:      oklch(0.620 0.130 75);
--seed-tint: oklch(0.945 0.050 75);
--seed-ink:  oklch(0.420 0.090 75);

/* Lines + lineage edges */
--border:        oklch(0.890 0.012 110);
--border-strong: oklch(0.800 0.018 110);
--edge:          oklch(0.520 0.110 150 / 0.40);  /* default lineage edge */
--edge-faded:    oklch(0.610 0.050 110 / 0.30);  /* dead edge */
--ring:          oklch(0.520 0.130 150 / 0.55);  /* focus ring */
```

**Banned:** any `#fff`/`gray-50` ground, `indigo-500`, `from-purple-* to-blue-*`, default Tailwind `blue-500`/`cyan-400`,
decorative color that doesn't encode data.

---

## 5. Motion philosophy — "Grow / Pulsate / Branch / Settle"

Motion reinforces biology; it is never decoration. Named after germination.

- **Compositor only:** `transform` + `opacity`. Never animate `height/top/left/width/margin`.
- **One orchestrated page-load reveal:** the survival **spine draws first** (seed→champion, `pathLength` 0→1,
  ~700ms `ease-out-organic`), then dead branches and the rest **fade in behind it** (staggered). Then quiet.
- **Live growth (every ~4s a generation lands):** new nodes **bud out of the parent's position** then spring to
  place (`type: spring`, soft); new edges grow `pathLength` 0→1; only the **delta** animates — everything already
  on screen holds still. Camera re-fits smoothly so the champion stays in frame.
- **Apoptosis:** loser transitions fill→**hollow** + strike draws over **600ms** (a 200ms fade reads as "loading";
  600ms reads as "death"). Permanent on next render — no oscillation.
- **Champion:** exactly **one** slow breathing halo. Nothing else pulses. One heartbeat in the frame.
- **Easing:** `--ease-organic: cubic-bezier(0.16, 1, 0.3, 1)`; springs settle, never linear ramps.
- **`prefers-reduced-motion: reduce`:** buds appear in place, spine snaps drawn, strikes snap, no breath, no
  parallax. Non-negotiable; verified in the polish pipeline.
- Library: **Motion** (`motion/react`). Cap simultaneous animations ~5 beyond the orchestrated load.

---

## 6. Spatial composition

- **Hero:** asymmetric, NOT centered-with-two-CTAs. Fraunces headline left (cols 1–6 on a 12-col grid); the
  living lineage tree bleeds right (cols 6–12), overlapping at col 6. The headline is the LCP element
  (server-rendered text); the tree hydrates and animates after.
- **Cell dashboard:** split — lineage tree (~60%) left, persistent prompt-diff inspector (~40%) right; the
  fitness curve a full-width footnote strip below. Two density modes are intentional: airy landing, dense cell.
- **No** three-card feature grid, **no** sticky backdrop-blur nav, **no** bento tiles. The story is told inline.
- Hairline ink rules (`--border`), not shadow cards. Square corners (≤2px radius). Generous air on the story
  surface; tabular density on the dashboard.

---

## 7. Backgrounds & texture

- **Paper grain** (feTurbulence `fractalNoise`, baseFrequency ~0.7, opacity ~0.045, `mix-blend-mode: multiply`)
  over the whole warm ground → "lab paper / agar," never flat.
- **Brightfield pool** behind the lineage canvas: a soft warm radial light (paper, slightly brighter center)
  + the faintest green/gold tints where the spine and champion sit — light pooling on a slide, NOT a dark vignette.
- Optional contour hairlines (fitness-landscape subtext) behind the tree — faint warm-grey iso-lines, only if it
  reads as depth and never as noise.
- No glassmorphism, no mesh gradients, no drop shadows above ~8px blur (one soft lift on the active node only).

---

## 8. Lineage tree encoding (the centerpiece) — exact rules

- **X = generation (time).** Faint generation gridlines + a `gen 0 →` axis with an arrowhead so time-direction
  is never ambiguous.
- **Y = fitness.** Sort/position siblings so higher fitness sits higher → the spine climbs. This is the headline.
- **Size = fitness** (redundant encoding). Champion largest.
- **Color = STATE only** (never fitness): alive-production = green, alive-experimental = methyl-violet, champion =
  gold, tombstoned = hollow grey ring. Two variables on one channel is banned.
- **Tombstoned (light-ground port):** **hollow ring, no fill** + strike-through + ~0.5 opacity (low-opacity grey
  fills vanish on white; hollow reads as a lysed/empty cell). Stays on canvas permanently.
- **Spine (light-ground port):** thickest stroke + full chroma (gold) + a soft drop-shadow — NOT additive glow
  (glow needs a dark backdrop). Contrast, not luminance, carries emphasis on light.
- **Edges:** curved bump (`linkHorizontal`/`curveBumpX`), **tapered** by descendant count (Murray's law) so the
  trunk is thick and twigs thin → organic, not org-chart. Nodes are circles (never rectangles), filled like
  stained cells with a hair of radial depth.
- **Labels (tiered):** seed + champion pills always; spine nodes always; off-spine alive on hover/focus;
  tombstoned never by default (hover reveals). Never render text < 10px — zoom to read.
- **Live growth:** budding enter from parent; only the delta animates; camera re-fits to keep champion in frame.

---

## 9. Anti-pattern checklist (each component PR verifies none present)

- [ ] Inter / Roboto / Space Grotesk / system-ui / Open Sans / Lato / Poppins / Montserrat
- [ ] `#fff` or `gray-50` page ground; flat white cards with soft grey drop-shadows
- [ ] purple→blue gradient; `indigo-500`; default `blue-500`/`cyan-400`; SaaS clinical blue accent
- [ ] dark-mode dashboard (the brief is LIGHT)
- [ ] centered hero + two CTAs ("Get Started"/"Learn More")
- [ ] three-card feature grid with lucide icons; bento tiles
- [ ] pill buttons with gradient bg; "Trusted by" logo strip; `10K+/99%/24/7` stats row
- [ ] sticky nav with `backdrop-blur`; testimonial carousel
- [ ] **a "● LIVE" pill / blinking status dot** (explicitly banned by the brief)
- [ ] stock DNA-helix / glowing-network / abstract-molecule hero render
- [ ] color that encodes nothing; rectangles as lineage nodes; orthogonal elbow edges
- [ ] additive glow as emphasis on the light ground; low-opacity grey "dead" elements that vanish on white
- [ ] `100vh` (use `100dvh`); layout-property transitions; missing `prefers-reduced-motion`
- [ ] missing `text-wrap: balance` on headlines / `pretty` on body

---

## 9.5 Polish-pipeline exceptions (baseline-ui / fixing-motion-performance)

These rules are intentionally overridden; each is a deliberate, scoped design decision, not slop.

1. **Animation is requested.** baseline-ui's "never animate unless requested" is overridden: the user explicitly
   asked for smooth page + element animation. All motion is compositor-only (`transform`/`opacity`/SVG
   `pathLength`), `prefers-reduced-motion`-guarded, and the one looping element (champion breath) pauses
   off-screen via IntersectionObserver.
2. **Organic easing curves.** `--ease-organic` and a gentle settle (`--ease-settle`, overshoot 1.3) are the
   requested "biological" motion. Used only on orchestrated reveals and the budding growth, never on interaction
   feedback (which stays instant).
3. **Letter-spacing on small caps.** `tracking-[0.14em–0.16em]` on sub-11px uppercase mono eyebrow labels is core
   to the Cell-journal editorial voice. No other `tracking-*` is used.
4. **Gradients are viz idioms, not decoration.** Three uses only: radial "stained-cell" node fills (depth on a
   round cell), the Recharts area-fill alpha gradient (a chart idiom), and the brightfield radial atmosphere on
   the lineage canvas. No decorative/purple gradients anywhere.
5. **Multiple colors = semantic status, not multiple accents.** Green (alive), gold (champion), methyl-violet
   (experimental), clay (apoptosed/removed) each encode data state (the cell-stain language). The single
   *decorative* accent is chlorophyll green.
6. **Custom tree keyboard behavior.** The SVG lineage nodes hand-roll keyboard/focus (tabindex + Enter/Space +
   aria-label) because no component primitive models a zoomable d3 lineage. Verified: Lighthouse a11y 100.

Lighthouse targets (verified on the prod build): Accessibility 100, Best Practices 100, SEO 100, Agentic 100;
LCP < 2.0s (measured 0.81s), CLS < 0.05 (measured 0.00).

## 10. Differentiation summary

1. **The lineage climbs.** Fitness is height; the spine ascends seed→champion. No other agent UI shows learning
   as a literal ascent you can watch grow on camera.
2. **Brightfield, not darkfield.** A warm Cell-journal figure on agar paper — the harder, more premium, more
   differentiated target than yet another dark dashboard.
3. **The dead stay.** Apoptosed strategies remain as hollow struck cells — a permanent record of what didn't work.
4. **One living green does the narrative.** Chlorophyll green → ripening gold binds tree, curve, and metrics
   (Nextstrain). Color is honest semantics (the cell-stain language), never decoration.
5. **Editorial serif in a data product.** Fraunces says "this is a real, written, citable thing" — not a template.
