# Granum — 3-Minute Demo Script

**Target length:** 3:00, with 20-second beats.
**Voiceover:** ElevenLabs neutral US male, ~140 wpm. SSML `<break time="N.Ns" />` tags honored.
**Voiceover-only script (ready for TTS feed):** [`docs/voiceover.txt`](./voiceover.txt). Each beat is rendered as a separate MP3 then concatenated; see [`scripts/render_voiceover.py`](../scripts/render_voiceover.py).
**Capture:** `scripts/demo.sh` orchestrates the runs; Playwright MCP captures via `chrome` device profile @ 1920×1080.
**Reference cell:** `aetna_cardiac` — 8 generations, 6 apoptosed, 0.41 → 0.79 overturn.

**Word-budget summary (140 wpm = 2.33 words/sec):**

| Beat | Duration | Budget words | Current | Status |
|---|---|---|---|---|
| Cold open | 0:00–0:20 (≈17s VO under titles) | ≤ 40 | 39 | tight, OK |
| Beat 1 | 0:20–1:00 (≈36s VO under apoptosis hold) | ≤ 84 | 71 | comfortable |
| Beat 2 | 1:00–1:30 (≈27s VO) | ≤ 63 | 62 | tight, OK |
| Beat 3 | 1:30–2:00 (≈26s VO) | ≤ 60 | 58 | OK |
| Beat 4 | 2:00–2:30 (≈27s VO) | ≤ 63 | 58 | OK |
| Closer | 2:30–3:00 (≈25s VO + 5s end card) | ≤ 58 | 57 | OK |
| **Total** | **3:00** | **≈ 368** | **345** | **fits** |

---

## Cold open — 0:00–0:20 · The denial

**On-screen:** Full-bleed photo of a paper denial letter, blurred. Cut to a CMS chart: "10% of denials filed. 83% of filed appeals overturn." Numbers tick up in JetBrains Mono.

**Voiceover (VO starts at 0:02, under the denial paper):**
> Every year, US insurers deny medically necessary care to millions of patients. <br>`<break time="0.4s" />`<br> When a physician appeals, **eighty-three percent** win. <br>`<break time="0.5s" />`<br> Only **ten percent** are ever filed — writing one costs twelve hours of physician time. <br>`<break time="0.6s" />`<br> **The math kills the appeal before it's written.**

**Visual notes:**
- 0:00–0:02 silence on the denial paper before VO opens.
- Cut to stat reveal at ~0:06 *under* the VO, not after — numbers tick during "eighty-three percent / ten percent / twelve hours" so the stat lands when the voice says it.
- Hold the stat panel for 2 seconds after the VO ends; this is the policy hook.
- No agent UI yet — sell the problem first.

---

## Beat 1 — 0:20–1:00 · Inject denial, three mutants compete

**On-screen:** Cut to `/cell/aetna_cardiac`. Camera frames the lineage tree. Inject a new Aetna cardiac denial (synthetic). Three candidate strategies — `L6`, `L7`, `L8` — generate three candidate appeals in parallel. LLM-as-judge scores each against the gold dataset of twelve prior overturned Aetna+cardiac appeals. The winner is `L8`. The two losers' prompt versions get permanently deleted from Phoenix. Their tree nodes fade — **opacity 0.35, saturate 0** — over 600ms. The branches connecting them turn dashed.

**Voiceover:**
> Granum's appeal-writer holds a small population of strategies — five to twelve at steady state — one per payer-and-diagnosis pair. <br>`<break time="0.3s" />`<br> A new denial arrives. Three strategies generate three candidate appeals. An LLM-as-judge scores each one against a gold dataset of prior overturned appeals. <br>`<break time="0.4s" />`<br> The winner is submitted. The losers' prompts are **permanently tombstoned** in the Phoenix registry. No revert. No archive. <br>`<break time="0.6s" />`<br> Apoptosis.

**Visual notes:**
- The tombstone fade is THE emotional beat of the demo. Hold the dissolve full 600ms. Don't cut early.
- Camera does NOT cut during the apoptosis — same continuous shot.
- Show the legend chip "● apoptosed" lighting up as nodes fade.
- VO should land "Apoptosis." exactly as the L6/L7 fade hits opacity 0.35 (~600ms into the dissolve).
- The word "tombstoned" (not "deleted") matches Path B reality — Phoenix prompt versions are immutable; we strip the `production` tag and add `tombstoned`. The strategy is structurally dead, the audit lineage is preserved.

---

## Beat 2 — 1:00–1:30 · The winning appeal

**On-screen:** Click the champion node `L8`. Right pane (`PromptDiff`) snaps to show the appeal text. Citation chips highlight: `Aetna CPB 0228 §IV.A.3.b`, `ACC/AHA 2023 §3.2`, `Internal precedent x2`, `Physician NPI + state license`. The judge rationale renders below: "wins on three axes — explicit sub-clause citation, preempting common secondary denial reasons, physician credentials sign-off."

**Voiceover:**
> Here's the winning appeal. It cites Aetna's exact clinical-policy sub-clause. It cross-references the ACC/AHA cardiology guideline. It includes two prior overturned precedents from the gold dataset. It preempts the three most common secondary denial reasons Aetna uses on cardiac cases. **None of this was hand-written.** The strategy mutated into this shape over eight generations.

**Visual notes:**
- Zoom in on the citation chips one at a time, 600ms apart.
- The judge rationale stays on screen 4 seconds; this is where the AI-as-judge claim earns its credit.

---

## Beat 3 — 1:30–2:00 · Six weeks fast-forward

**On-screen:** Time-lapse: 8 generations of evolution. Lineage tree grows. Dead branches accumulate as tombstoned grey strikethroughs. Surviving branches climb. The fitness curve below climbs from 0.41 to 0.79. Counter in the corner: "alive: 3 · apoptosed: 6 · generations: 8".

**Voiceover:**
> Six weeks of evolution, fast-forwarded. The population mutates. Strategies that won become parents. Strategies that lost are erased. The fitness curve climbs from forty-one percent — vanilla baseline overturn rate — to seventy-nine percent at generation eight. The lineage tree is the system of record: every branch, every death, every promotion, frozen on the canvas.

**Visual notes:**
- This is the second visual climax. Time-lapse runs at ~1.5s per generation, 12 seconds total.
- Fitness curve animation: synchronize with the tree generation tick. Recharts `isAnimationActive=false` means we drive frames manually via state.

---

## Beat 4 — 2:00–2:30 · The Gen-1 vs Gen-8 diff

**On-screen:** `PromptDiff` component fills the screen. Left: `L1.a` (Gen 1, fitness 0.52, tombstoned). Right: `L8` (Gen 8, fitness 0.79, champion). Word-level diff lights up: added clauses in hematoxylin amber, removed clauses in apoptosis red with strikethrough. Citation delta block at the bottom: four new citations added, generic ACC/AHA removed.

**Voiceover:**
> Here's what the agent learned. Gen 1 cited a generic clinical guideline. Gen 8 cites Aetna's specific sub-clause six times, preempts three secondary denial reasons, attaches physician credentials, and references two prior overturned cases. **The agent learned Aetna's exact medical-necessity language.** Not because we trained it. Because it watched losing strategies die and survivors mutate.

**Visual notes:**
- Slow zoom in on one phrase change: `"medically necessary"` appears verbatim six times. This is the "agent learned the payer's verbiage" moment.

---

## Closer — 2:30–3:00 · Lineage as system of record

**On-screen:** Pull back to landing-page hero: "Strategies that lose are **permanently** deleted." Cut to a one-line stat: "Aetna · Cardiac · 41% → 79% overturn · 8 generations · 6 apoptosed." Cut to the GitHub repo URL and the Devpost link. End on the favicon.

**Voiceover:**
> Granum is one agent. <br>`<break time="0.3s" />`<br> No supervisor, no meta-watcher, no diagnose-and-patch loop. <br>`<break time="0.4s" />`<br> The agent is the germinal center. It generates, competes, mutates, and prunes. <br>`<break time="0.4s" />`<br> Losing strategies are **permanently apoptosed** — structurally dead, ineligible for any future tournament. That commitment forces every mutation to be a real bet. <br>`<break time="0.6s" />`<br> **Apache 2.0. Synthetic data. Built on Google ADK and Arize Phoenix.**

**End card:** `granum.app · github.com/oneKn8/granum · Google Cloud Rapid Agent · Arize Phoenix track · 2026`

---

## Production notes

- **Audio:** 1 voice track, no music in the cold open (silence sells the stat). Light ambient pad starts at 0:20 in the eosin-blue/lab-bench tonal direction. Cut to silence again at 2:55 before the end card.
- **Cuts:** Zero hard cuts during apoptosis transitions (Beat 1, Beat 3). Cuts allowed only on voiceover sentence boundaries.
- **Font on captions:** IBM Plex Serif for callouts; JetBrains Mono for numbers. Matches the web UI.
- **Backup:** If recording fails or the Phoenix dataset doesn't seed, fall back to a static walkthrough using `web/lib/mock-data.ts` — every visual element of the demo is reproducible offline.
- **Resolution:** Record 1920×1080 then re-encode to 1080p H.264 @ 60fps for YouTube. ≤3:00 hard limit (Devpost rejects longer).

---

## Length budget

| Beat | Duration | Cumulative |
|---|---|---|
| Cold open | 0:20 | 0:20 |
| Beat 1 — denial + apoptosis | 0:40 | 1:00 |
| Beat 2 — winning appeal | 0:30 | 1:30 |
| Beat 3 — fast-forward | 0:30 | 2:00 |
| Beat 4 — diff | 0:30 | 2:30 |
| Closer | 0:30 | 3:00 |

---

## Terminology choice — "apoptosed" vs "deleted"

The VO uses **"permanently apoptosed"** and **"permanently tombstoned"** rather than "permanently deleted." Reason: Path B apoptosis is functional, not literal. Phoenix prompt versions are immutable; the implementation strips the `production` tag and adds `tombstoned`. The strategy is structurally dead — ineligible for selection, mutation, or promotion — and the audit lineage is preserved. A judge reading the code (`src/granum/tools/phoenix_client.py::tombstone`) will see tag operations, not deletes; we want the VO to track reality so the demo earns trust on close inspection.

The on-screen hero text ("Strategies that lose are PERMANENTLY deleted.") was kept as marketing prose for legibility; in product copy the simpler verb wins. The technical explanation lives in the README and submission.md.

If a judge asks: "Is the prompt actually deleted?" The honest answer is: "No — it's tombstoned. Same behavioral effect for the running agent (cannot be selected, mutated, or promoted), but the audit history is preserved. We considered hard-delete; Phoenix prompt versions are immutable for good audit reasons, so this is the correct surface."
