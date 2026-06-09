# Granum — Visual Storyboard

Frame-by-frame companion to [`demo-script.md`](./demo-script.md). Each frame is roughly one second of video; held frames are noted.

`screenshot:` placeholders point to artifacts that `scripts/demo.sh` produces under `videos/storyboard/`.

Tree-node key: `o` = live strategy, `x` = apoptosed strategy, `*` = champion.

---

## Frame 01 · 0:00 · Cold open

```
+---------------------------------------------------------------+
|                                                               |
|              [paper denial, blurred 70%, b/w]                 |
|                                                               |
+---------------------------------------------------------------+
```

`screenshot: denial_paper_blur.png`

Held 4 seconds. Silence under VO until "83 percent".

---

## Frame 02 · 0:08 · The AMA stat reveal

```
+---------------------------------------------------------------+
|                                                               |
|   10% filed.  83% of filed appeals overturn.                  |
|   12 hrs/wk per physician.                                    |
|                                                               |
|         IBM Plex Serif 64pt · eosin-blue accent on 10/83/12   |
+---------------------------------------------------------------+
```

`screenshot: stat_reveal.png`

Numbers tick up via JS `requestAnimationFrame` from 0 to target. 800ms each.

---

## Frame 03 · 0:20 · Cut to /cell/aetna_cardiac

```
+---------------------------------------------------------------+
| Granum   AETNA · CARDIAC      [ Aetna | United | Anthem |...] |
+---------------------------------------------------------------+
| PAYER  Aetna  | DX  Cardiac dx imaging | GENS 10 | 3 alive   |
+---------------------------------------------------------------+
| [appeal-writer lineage] [co-evolution]                        |
| Appeal-writer population                       3 alive · 18 x |
|                                                               |
|   o--o--o--o--o--o                                            |
|     \  \   \                                                  |
|      o  x   x  (faded greys, apoptosed)                       |
|                                                               |
+---------------------------------------------------------------+
```

`screenshot: cell_pre_denial.png`

Camera dolly-in on the lineage tree, ~600ms.

---

## Frame 04 · 0:32 · Inject denial

```
+---------------------------------------------------------------+
| New denial received · CPB-0228-NM · I25.10                    |
| Aetna · 2 seconds ago                                         |
+---------------------------------------------------------------+
| (lineage tree highlights three candidates)                    |
|                                                               |
|   o--o--o--o--o--[c1]                                         |
|     \  \   \    \                                            |
|      o  x   x   [c2]                                          |
|                  \                                            |
|                  [c3]                                         |
+---------------------------------------------------------------+
```

`screenshot: denial_injected.png`

The three candidates each get a 1px eosin-blue selection ring drawn with a 200ms ease-out scale-in.

---

## Frame 05 · 0:42 · The tournament & apoptosis (THE BEAT)

```
+---------------------------------------------------------------+
| Tournament · 3 candidates                                     |
|                                                               |
|   c1 -> score 0.94      x  apoptosed                          |
|   c2 -> score 0.96      x  apoptosed                          |
|   c3 -> score 0.98      *  WINNER (champion)                  |
|                                                               |
| (c1, c2 nodes fade: opacity 1.0 -> 0.35,                      |
|  filter saturate(1) -> saturate(0), 600ms ease-out.          |
|  Edges to c1, c2 turn dashed.)                                |
+---------------------------------------------------------------+
```

`screenshot: apoptosis_in_progress.png` (mid-transition, t=300ms)
`screenshot: apoptosis_complete.png`

**This is the emotional beat.** Do not cut. Hold the dissolve full 600ms then linger 800ms on the new state. The eye needs time to process "they're really gone."

---

## Frame 06 · 0:52 · Champion selected, PromptDiff renders

```
+---------------------------------------------------------------+
| Appeal-writer population              | Prompt diff           |
| (champion marked *)                   | parent -> champion    |
|   o--o--o--o--o--*                     |                       |
|     \  \   \  \  \                     | mutation · champion:  |
|      x  x   x  x  x                    | §IV.A.3.b sub-clause  |
|                                       | + physician credentials|
|                                       |                       |
|                                       | PARENT                |
|                                       | Frame as Aetna CPB    |
|                                       | 0228 §IV.A.3 ...      |
|                                       |                       |
|                                       | MUTANT (champion)     |
|                                       | Frame as Aetna CPB    |
|                                       | 0228 §IV.A.3 [with    |
|                                       | explicit §IV.A.3.b    |
|                                       | sub-clause attribution]|
+---------------------------------------------------------------+
```

`screenshot: champion_diff.png`

Camera holds. VO calls out the four citation chips one at a time.

---

## Frame 07 · 1:16 · Fast-forward — generation tick

```
+---------------------------------------------------------------+
| GEN 1  · fitness 0.40                                         |
| GEN 2  · fitness 0.52 up                                      |
| GEN 3  · fitness 0.61 up                                      |
| GEN 4  · fitness 0.70 up                                      |
| GEN 5  · fitness 0.77 up                                      |
| GEN 6  · fitness 0.83 up                                      |
| GEN 7  · fitness 0.88 up                                      |
| GEN 8  · fitness 0.92 up                                      |
| GEN 9  · fitness 0.95 up                                      |
| GEN 10 · fitness 0.98 *                                       |
|                                                               |
| (tree grows in time-lapse; fitness curve climbs synchronously)|
+---------------------------------------------------------------+
```

`screenshot: timelapse_gen3.png`
`screenshot: timelapse_gen6.png`
`screenshot: timelapse_gen10.png` (three keyframes for the video editor)

~12 seconds, ~1.2s per generation tick. Tombstones accumulate visibly.

---

## Frame 08 · 1:36 · Fitness curve climb closeup

```
+---------------------------------------------------------------+
|  1.0 ┤                                       *──────── 0.98   |
|      │                          ┌─────────────              |
|  0.8 ┤              ┌───────────┘                             |
|      │    ┌─────────┘                                         |
|  0.6 ┤┌───┘                                                   |
|      ││                                                       |
|  0.4 ┤└ baseline 0.40                                         |
|      └───────────────────────────────────────────────────    |
|       1   2   3   4   5   6   7   8   9   10                  |
+---------------------------------------------------------------+
```

`screenshot: fitness_curve_final.png`

Champion-amber line dominates; eosin-blue area shaded below. Annotation callout: "+58pp absolute lift."

---

## Frame 09 · 1:46 · Gen 1 vs champion PromptDiff full-screen

```
+---------------------------------------------------------------+
| Prompt diff — gen 1 seed -> champion (gen 10) · 0.40 -> 0.98  |
|                                                               |
| PARENT · GEN 1                | MUTANT · CHAMPION             |
| Frame the appeal as an Aetna  | Frame as Aetna CPB 0228       |
| Clinical Policy Bulletin 0228 | §IV.A.3 compliance with       |
| compliance argument. Cite     | explicit §IV.A.3.b sub-clause |
| Section IV.A subsection 3.    | attribution. ACC/AHA 2023     |
|                               | §3.2 cross-cite. Two prior    |
|                               | overturned precedents.        |
|                               | 'Medically necessary' verbatim|
|                               | several times. Preempt three  |
|                               | secondary denial reasons      |
|                               | (insufficient duration, missed|
|                               | step-therapy, no specialist   |
|                               | referral) with structured     |
|                               | affirmative exhibits A, B, C.  |
|                               | Sign off with attending       |
|                               | physician credentials + NPI + |
|                               | state license number.         |
|                                                               |
| CITATION DELTA                                                |
|   + Aetna CPB 0228 §IV.A.3.b                                  |
|   + ACC/AHA 2023 §3.2                                         |
|   + Internal precedent x2                                     |
|   + Physician NPI + state license                             |
|   - Generic ACC/AHA guidelines                               |
+---------------------------------------------------------------+
```

`screenshot: gen1_vs_champion_diff.png`

Slow camera zoom on the phrase "medically necessary verbatim", the moment the agent's learning is visible.

---

## Frame 10 · 2:10 · Second cell + cross-cell transfer

```
+---------------------------------------------------------------+
| UNITED · ONCOLOGY    0.62 -> 0.98 · 10 gens · 18 apoptosed   |
|                                                               |
|   o--o--o--o--o--*  (its own lineage climbs)                  |
|                                                               |
+---------------------------------------------------------------+
| CROSS-CELL TRANSFER                                           |
|   united_oncology -> aetna_cardiac                            |
|        +0.19 lift · p = 0.024 · PROMOTED                      |
|   aetna_cardiac -> united_oncology                           |
|        rejected · 5/5 failed negative selection              |
+---------------------------------------------------------------+
```

`screenshot: second_cell_and_transfer.png`

Switch the cell selector to `united_oncology` first (its tree + fitness curve render), then cut to the transfer view. Hold the rejected edge 2 seconds; the asymmetry is the point.

---

## Frame 11 · 2:38 · Pull back to hero

```
+---------------------------------------------------------------+
|                                                               |
|   Strategies that lose                                        |
|   are PERMANENTLY retired.                                    |
|                                                               |
|   (apoptosis-red on "permanently")                            |
|                                                               |
|                                       [lineage preview tree]  |
|                                                               |
+---------------------------------------------------------------+
```

`screenshot: hero_closer.png`

Same composition as the live landing page; this is the closure callback.

---

## Frame 12 · 2:52 · Numbers banner + end card

```
+---------------------------------------------------------------+
| Aetna · Cardiac · 40% -> 98% · 10 generations                |
| 18 apoptosed · 3 alive                                        |
+---------------------------------------------------------------+
| granum-oneknights-projects.vercel.app                        |
| github.com/oneKn8/granum                                      |
| Google Cloud Rapid Agent · Arize Phoenix · 2026              |
|                                                               |
|   [Granum favicon — lineage motif]                            |
+---------------------------------------------------------------+
```

`screenshot: end_card.png`

Hold 5 seconds. Apache-2.0 + synthetic-data disclaimer in fine print at the bottom.

---

## Capture order

`scripts/demo.sh` produces frames in this order (each is one Playwright snapshot):

1. `denial_paper_blur.png` — static asset, hand-prepared in `videos/assets/`
2. `stat_reveal.png` — rendered from a one-off `/_demo/stats` route (TBD if time)
3. `cell_pre_denial.png` — `/cell/aetna_cardiac`, before injecting denial
4. `denial_injected.png` — after `granum cycle --cell aetna_cardiac`, post-render
5. `apoptosis_in_progress.png` — Playwright screenshots the tree at t=300ms (delay 300, snapshot)
6. `apoptosis_complete.png` — t=800ms post-transition
7. `champion_diff.png` — click the champion, snapshot of the PromptDiff
8. `timelapse_gen{3,6,10}.png` — three checkpoints during the evolve loop
9. `fitness_curve_final.png` — closeup screenshot of the Recharts canvas
10. `gen1_vs_champion_diff.png` — gen-1 seed vs champion override
11. `second_cell_and_transfer.png` — switch to `united_oncology`, then the transfer view
12. `hero_closer.png` — `/`, scrolled to top
13. `end_card.png` — `/_demo/end-card` (or static `videos/assets/end_card.svg`)
