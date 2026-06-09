# Granum — 3-Minute Demo Script

**Target length:** 3:00.
**Voiceover:** ElevenLabs neutral US male, ~140 wpm. SSML `<break time="N.Ns" />` tags honored.
**Voiceover-only script (ready for TTS feed):** [`docs/voiceover.txt`](./voiceover.txt). Each beat is rendered as a separate MP3 then concatenated; see [`scripts/render_voiceover.py`](../scripts/render_voiceover.py).
**Capture:** `scripts/demo.sh` orchestrates the runs; Playwright MCP captures via `chrome` device profile @ 1920x1080.
**Reference cell:** `aetna_cardiac`, 10 generations, 18 apoptosed, 0.40 -> 0.98 judge-rated overturn likelihood. Second cell `united_oncology`: 0.62 -> 0.98.

**Word-budget summary (140 wpm = 2.33 words/sec):**

| Beat | Duration | Budget words | Current | Status |
|---|---|---|---|---|
| Cold open | 0:00-0:20 | <= 40 | 39 | OK |
| Beat 1 | 0:20-0:52 | <= 75 | 71 | OK |
| Beat 2 | 0:52-1:16 | <= 56 | 54 | OK |
| Beat 3 | 1:16-1:46 | <= 65 | 55 | OK |
| Beat 4 | 1:46-2:10 | <= 56 | 50 | OK |
| Beat 5 | 2:10-2:38 | <= 62 | 57 | OK |
| Closer | 2:38-3:00 | <= 55 | 52 | OK |
| **Total** | **3:00** | **~409** | **378** | **fits** |

---

## Cold open — 0:00-0:20 · The denial

**On-screen:** Full-bleed photo of a paper denial letter, blurred. Cut to a CMS chart: "10% of denials filed. 83% of filed appeals overturn." Numbers tick up in JetBrains Mono.

**Voiceover (VO starts at 0:02, under the denial paper):**
> Every year, US insurers deny medically necessary care to millions of patients. <br>`<break time="0.4s" />`<br> When a physician appeals, **eighty-three percent** win. <br>`<break time="0.5s" />`<br> Only **ten percent** are ever filed. Writing one costs twelve hours of physician time. <br>`<break time="0.6s" />`<br> **The math kills the appeal before it's written.**

**Visual notes:**
- 0:00-0:02 silence on the denial paper before VO opens.
- Cut to stat reveal at ~0:06 *under* the VO, not after. Numbers tick during "eighty-three percent / ten percent / twelve hours".
- Hold the stat panel for 2 seconds after the VO ends; this is the policy hook.
- No agent UI yet. Sell the problem first.

---

## Beat 1 — 0:20-0:52 · Inject denial, three mutants compete

**On-screen:** Cut to `/cell/aetna_cardiac`. Camera frames the lineage tree. Inject a new Aetna cardiac denial (synthetic). Three candidate strategies generate three candidate appeals in parallel. LLM-as-judge scores each against the gold dataset of twelve prior overturned Aetna+cardiac appeals. The winner survives. The two losing strategies' prompt versions are tombstoned in Phoenix. Their tree nodes fade (**opacity 0.35, saturate 0**) over 600ms. The branches connecting them turn dashed.

**Voiceover:**
> Granum's appeal-writer holds a small population of strategies, five to twelve at steady state, one per payer-and-diagnosis pair. <br>`<break time="0.3s" />`<br> A new denial arrives. Three strategies generate three candidate appeals. An LLM-as-judge scores each one against a gold dataset of prior overturned appeals. <br>`<break time="0.4s" />`<br> The winner is submitted. The losers' prompts are **permanently tombstoned** in the Phoenix registry. No revert. No archive. <br>`<break time="0.6s" />`<br> Apoptosis.

**Visual notes:**
- The tombstone fade is THE emotional beat of the demo. Hold the dissolve full 600ms. Don't cut early.
- Camera does NOT cut during the apoptosis. Same continuous shot.
- Show the legend chip "apoptosed" lighting up as nodes fade.
- VO should land "Apoptosis." exactly as the losing nodes fade to opacity 0.35.
- The word "tombstoned" matches reality. Phoenix prompt versions are immutable; Granum strips the `production` tag and adds `tombstoned`. The strategy is structurally dead, the audit lineage is preserved.

---

## Beat 2 — 0:52-1:16 · The winning appeal

**On-screen:** Click the champion node. Right pane (`PromptDiff`) snaps to show the appeal text. Citation chips highlight: `Aetna CPB 0228 §IV.A.3.b`, `ACC/AHA 2023 §3.2`, `Internal precedent x2`, `Physician NPI + state license`. The judge rationale renders below: "wins on three axes: explicit sub-clause citation, preempting common secondary denial reasons, physician credentials sign-off."

**Voiceover:**
> Here's the winning appeal. It cites Aetna's exact clinical-policy sub-clause. It cross-references the ACC/AHA cardiology guideline. It includes two prior overturned precedents. It preempts the three most common secondary denial reasons Aetna uses on cardiac cases. **None of this was hand-written.** The strategy mutated into this shape over ten generations.

**Visual notes:**
- Zoom in on the citation chips one at a time, 600ms apart.
- The judge rationale stays on screen 4 seconds; this is where the LLM-as-judge claim earns its credit.

---

## Beat 3 — 1:16-1:46 · Fast-forward through ten generations

**On-screen:** Time-lapse: 10 generations of evolution. Lineage tree grows. Dead branches accumulate as tombstoned grey strikethroughs. Surviving branches climb. The fitness curve below climbs from 0.40 to 0.98. Counter in the corner: "alive: 3 · apoptosed: 18 · generations: 10".

**Voiceover:**
> Ten generations of evolution, fast-forwarded. The population mutates. Strategies that won become parents. Strategies that lost are erased. The fitness curve climbs from forty percent, the vanilla baseline overturn likelihood, to ninety-eight percent. The lineage tree is the system of record: every branch, every death, every promotion, frozen on the canvas.

**Visual notes:**
- This is the second visual climax. Time-lapse runs at ~1.2s per generation, ~12 seconds total.
- Fitness curve animation: synchronize with the tree generation tick. Recharts `isAnimationActive=false` means we drive frames manually via state.

---

## Beat 4 — 1:46-2:10 · The Gen-1 vs champion diff

**On-screen:** `PromptDiff` component fills the screen. Left: Gen 1 seed strategy (tombstoned). Right: the Gen-10 champion (fitness 0.98). Word-level diff lights up: added clauses in hematoxylin amber, removed clauses in apoptosis red with strikethrough. Citation delta block at the bottom: four new citations added, generic ACC/AHA removed.

**Voiceover:**
> Here's what the agent learned. Generation one cited a generic clinical guideline. The champion cites Aetna's specific sub-clause, preempts three secondary denial reasons, attaches physician credentials, and references two prior overturned cases. **It learned Aetna's exact medical-necessity language.** Not because I trained it. Because it watched losing strategies die.

**Visual notes:**
- Slow zoom in on one phrase change: `"medically necessary"` appears verbatim several times. This is the "agent learned the payer's verbiage" moment.

---

## Beat 5 — 2:10-2:38 · Second cell + cross-cell transfer

**On-screen:** Switch the cell selector to `united_oncology`. Its lineage tree and fitness curve render — 0.62 -> 0.98 over 10 generations. Then open the transfer view (`/api/transfers`). Show the promoted edge: `united_oncology -> aetna_cardiac`, with the on-screen badge "**+0.19 lift · p = 0.024 · promoted**". Below it, the rejected edge `aetna_cardiac -> united_oncology` marked "rejected · 5/5 failed negative selection".

**Voiceover:**
> And it isn't one cell. A second cell, United oncology, evolved the same way, sixty-two to ninety-eight percent. Then a champion crossed between cells. The oncology strategy, dropped into the cardiac cell, gave a significant lift, p equals zero point zero two four, so it was promoted. The reverse was rejected. Too citation-rigid to generalize. Honest transfer.

**Visual notes:**
- On screen, show the lift as **+0.19** (the normalized UI value) with **p = 0.024**. The VO says "a significant lift" to avoid scale confusion between the +1.92 composite and the +0.19 normalized number.
- Hold the rejected edge for 2 seconds. The asymmetry is the point. Transfer works only when a strategy is general enough to survive a new antigen.

---

## Closer — 2:38-3:00 · Lineage as system of record

**On-screen:** Pull back to landing-page hero: "Strategies that lose are **permanently** retired." Cut to a one-line stat: "Aetna · Cardiac · 40% -> 98% · 10 generations · 18 apoptosed." Cut to the GitHub repo URL and the Devpost link. End on the favicon.

**Voiceover:**
> Granum is one agent. <br>`<break time="0.3s" />`<br> No supervisor, no meta-watcher, no diagnose-and-patch loop. <br>`<break time="0.4s" />`<br> The agent is the germinal center. It generates, competes, mutates, and prunes. <br>`<break time="0.4s" />`<br> Losing strategies are **permanently apoptosed**, which forces every mutation to be a real bet. <br>`<break time="0.6s" />`<br> **Apache 2.0. Synthetic data. Built on Google ADK and Arize Phoenix.**

**End card:** `github.com/oneKn8/granum · Google Cloud Rapid Agent · Arize Phoenix track · 2026`

---

## Production notes

- **Audio:** 1 voice track, no music in the cold open (silence sells the stat). Light ambient pad starts at 0:20. Cut to silence again before the end card.
- **Cuts:** Zero hard cuts during apoptosis transitions (Beat 1, Beat 3). Cuts allowed only on voiceover sentence boundaries.
- **Font on captions:** IBM Plex Serif for callouts; JetBrains Mono for numbers. Matches the web UI.
- **Backup:** If recording fails or the live API is down, fall back to the deterministic offline data path in `web/lib/`. Every visual element of the demo is reproducible offline.
- **Resolution:** Record 1920x1080 then re-encode to 1080p H.264 @ 60fps. 3:00 hard limit (Devpost rejects longer).

---

## Length budget

| Beat | Duration | Cumulative |
|---|---|---|
| Cold open | 0:20 | 0:20 |
| Beat 1 — denial + apoptosis | 0:32 | 0:52 |
| Beat 2 — winning appeal | 0:24 | 1:16 |
| Beat 3 — fast-forward | 0:30 | 1:46 |
| Beat 4 — diff | 0:24 | 2:10 |
| Beat 5 — second cell + transfer | 0:28 | 2:38 |
| Closer | 0:22 | 3:00 |

---

## Terminology choice — "apoptosed" vs "deleted"

The VO uses **"permanently apoptosed"** and **"permanently tombstoned"** rather than "permanently deleted." Reason: apoptosis here is functional, not literal. Phoenix prompt versions are immutable; the implementation strips the `production` tag and adds `tombstoned`. The strategy is structurally dead (ineligible for selection, mutation, or promotion) and the audit lineage is preserved. A judge reading the code will see tag operations, not deletes; the VO tracks reality so the demo earns trust on close inspection.

If a judge asks "is the prompt actually deleted?" the honest answer is: "No, it's tombstoned. Same behavioral effect for the running agent (cannot be selected, mutated, or promoted), but the audit history is preserved. Phoenix prompt versions are immutable for good audit reasons, so this is the correct surface."
