# Granum — Visual Storyboard

Frame-by-frame companion to [`demo-script.md`](./demo-script.md). Each frame is roughly one second of video; held frames are noted.

`screenshot:` placeholders point to artifacts that `scripts/demo.sh` produces under `videos/storyboard/`.

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
| Granum   AETNA · CARDIAC      [ Aetna | UHC | Anthem | ... ]  |
+---------------------------------------------------------------+
| PAYER  Aetna  | DX  Cardiac dx imaging | GENS 7  | 3·5  | ... |
+---------------------------------------------------------------+
| [appeal-writer lineage] [co-evolution]                        |
| Appeal-writer population                          3 alive · 5 |
|                                                               |
|   ○──○──○──○──○──○                                            |
|     \  \   ↘                                                  |
|      ○  ○   ⊗  (faded greys at gen 5..6)                      |
|                                                               |
+---------------------------------------------------------------+
```

`screenshot: cell_pre_denial.png`

Camera dolly-in on the lineage tree, ~600ms.

---

## Frame 04 · 0:35 · Inject denial

```
+---------------------------------------------------------------+
| New denial received · CPB-0228-NM · I25.10                    |
| Aetna · 2 seconds ago                                         |
+---------------------------------------------------------------+
| (lineage tree highlights L6, L7, L8 as candidates)            |
|                                                               |
|   ○──○──○──○──○──[L6]                                         |
|     \  \   ↘   ↘ \                                            |
|      ○  ○   ⊗   [L7]                                          |
|                  \                                            |
|                  [L8]                                         |
+---------------------------------------------------------------+
```

`screenshot: denial_injected.png`

L6, L7, L8 each get a 1px eosin-blue selection ring drawn with a 200ms ease-out scale-in.

---

## Frame 05 · 0:45 · The tournament & apoptosis (THE BEAT)

```
+---------------------------------------------------------------+
| Tournament · 3 candidates · gen 8                             |
|                                                               |
|   L6 → score 0.77      ⨯  apoptosed                           |
|   L7 → score 0.78      ⨯  apoptosed                           |
|   L8 → score 0.79      ★  WINNER (champion)                   |
|                                                               |
| (L6, L7 nodes fade: opacity 1.0 → 0.35,                       |
|  filter saturate(1) → saturate(0), 600ms ease-out.            |
|  Edges to L6, L7 turn dashed.)                                |
+---------------------------------------------------------------+
```

`screenshot: apoptosis_in_progress.png` (mid-transition, t=300ms)
`screenshot: apoptosis_complete.png`

**This is the emotional beat.** Do not cut. Hold the dissolve full 600ms then linger 800ms on the new state. The eye needs time to process "they're really gone."

---

## Frame 06 · 1:00 · L8 selected, PromptDiff renders

```
+---------------------------------------------------------------+
| Appeal-writer population              | Prompt diff           |
|                                       | L6 → L8               |
|   ○──○──○──○──○──L8 (champion ★)      |                       |
|     \  \   ↘ ↘ ↘                      | mutation · champion:  |
|      ⊗  ⊗   ⊗  ⊗                      | §IV.A.3.b sub-clause  |
|                                       | + physician credentials|
|                                       |                       |
|                                       | PARENT · GEN 6        |
|                                       | Frame as Aetna CPB    |
|                                       | 0228 §IV.A.3 ...      |
|                                       |                       |
|                                       | MUTANT · GEN 8        |
|                                       | Frame as Aetna CPB    |
|                                       | 0228 §IV.A.3 [with    |
|                                       | explicit §IV.A.3.b    |
|                                       | sub-clause attribution]|
+---------------------------------------------------------------+
```

`screenshot: champion_diff.png`

Camera holds. VO calls out the four citation chips one at a time.

---

## Frame 07 · 1:30 · Fast-forward — generation tick

```
+---------------------------------------------------------------+
| GEN 1 · fitness 0.52                                          |
| GEN 2 · fitness 0.58 ↑                                        |
| GEN 3 · fitness 0.64 ↑                                        |
| GEN 4 · fitness 0.69 ↑                                        |
| GEN 5 · fitness 0.74 ↑                                        |
| GEN 6 · fitness 0.77 ↑                                        |
| GEN 7 · fitness 0.78 ↑                                        |
| GEN 8 · fitness 0.79 ★                                        |
|                                                               |
| (tree grows in time-lapse; fitness curve climbs synchronously)|
+---------------------------------------------------------------+
```

`screenshot: timelapse_gen3.png`
`screenshot: timelapse_gen6.png`
`screenshot: timelapse_gen8.png` (three keyframes for the video editor)

12 seconds, ~1.5s per generation tick. Tombstones accumulate visibly.

---

## Frame 08 · 1:55 · Fitness curve climb closeup

```
+---------------------------------------------------------------+
|  1.0 ┤                                                        |
|      │                                       ★────────────    |
|  0.8 ┤                          ┌─────────────              champion 0.79 |
|      │              ┌───────────┘                             |
|  0.6 ┤    ┌─────────┘                                         |
|      │┌───┘                                                   |
|  0.4 ┤└baseline 0.41                                          |
|      └───────────────────────────────────────────────────     |
|       0   1   2   3   4   5   6   7   8                       |
+---------------------------------------------------------------+
```

`screenshot: fitness_curve_final.png`

Champion-amber line dominates; eosin-blue area shaded below. Annotation callout: "+38pp absolute lift."

---

## Frame 09 · 2:10 · Gen 1 vs Gen 8 PromptDiff full-screen

```
+---------------------------------------------------------------+
| Prompt diff — L1.a → L8 (gen 1 → gen 8) · 0.52 → 0.79         |
|                                                               |
| PARENT · GEN 1                | MUTANT · GEN 8                |
| Frame the appeal as an Aetna  | Frame as Aetna CPB 0228       |
| Clinical Policy Bulletin 0228 | §IV.A.3 compliance with       |
| compliance argument. Cite     | explicit §IV.A.3.b sub-clause |
| Section IV.A subsection 3.    | attribution. ACC/AHA 2023     |
|                               | §3.2 cross-cite. Two prior    |
|                               | overturned precedents.        |
|                               | 'Medically necessary' verbatim|
|                               | x6. Preempt three secondary   |
|                               | denial reasons (insufficient  |
|                               | duration, missed step-therapy,|
|                               | no specialist referral) with  |
|                               | structured affirmative        |
|                               | exhibits A, B, C. Sign off    |
|                               | with attending physician      |
|                               | credentials + NPI + state     |
|                               | license number.               |
|                                                               |
| CITATION DELTA                                                |
|   + Aetna CPB 0228 §IV.A.3.b                                  |
|   + ACC/AHA 2023 §3.2                                         |
|   + Internal precedent x2                                     |
|   + Physician NPI + state license                             |
|   − Generic ACC/AHA guidelines                                |
+---------------------------------------------------------------+
```

`screenshot: gen1_vs_gen8_diff.png`

Slow camera zoom on the phrase "medically necessary verbatim x6" — the moment the agent's learning is visible.

---

## Frame 10 · 2:35 · Pull back to hero

```
+---------------------------------------------------------------+
|                                                               |
|   Strategies that lose                                        |
|   are PERMANENTLY deleted.                                    |
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

## Frame 11 · 2:50 · Numbers banner + end card

```
+---------------------------------------------------------------+
| Aetna · Cardiac · 41% → 79% overturn · 8 generations          |
| 6 apoptosed · 3 alive                                         |
+---------------------------------------------------------------+
| granum.app                                                    |
| github.com/oneKn8/granum                                      |
| Google Cloud Rapid Agent · Arize Phoenix · 2026               |
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
4. `denial_injected.png` — after `granum cycle --cell aetna_cardiac --dry-run`, post-render
5. `apoptosis_in_progress.png` — Playwright screenshots the tree at t=300ms (delay 300, snapshot)
6. `apoptosis_complete.png` — t=800ms post-transition
7. `champion_diff.png` — click L8, snapshot of `/cell/aetna_cardiac?selected=bc_ae_012`
8. `timelapse_gen{3,6,8}.png` — three checkpoints during the cycle loop
9. `fitness_curve_final.png` — closeup screenshot of the Recharts canvas
10. `gen1_vs_gen8_diff.png` — set selectedId=bc_ae_002 and parent override → bc_ae_012
11. `hero_closer.png` — `/`, scrolled to top
12. `end_card.png` — `/_demo/end-card` (or static `videos/assets/end_card.svg`)
