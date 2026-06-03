# Spec — "The Living Immune System": activating Granum's dormant moat

**Date:** 2026-06-03 · **Status:** approved (design), pending implementation plan
**Author:** Shifat (Claude-assisted) · **Deadline context:** Google Cloud Rapid Agent Hackathon, Arize track, 2026-06-11 14:00 PDT
**Supersedes nothing** — this is additive to the shipped single-population germinal loop (main @ `3fc99b1`).

---

## 1. Objective

Turn Granum from *one* visible evolutionary loop into a *visible, multi-mechanism immune system* by making
the four built-but-dormant mechanisms live and demoed, plus hardening fitness honesty.

This maximizes the two highest-weighted Arize criteria — **Technical Implementation** (the #1 tie-breaker) and
**"quality of the agent's self-improvement loop"** (a named Arize criterion) — and **structurally answers the single
load-bearing critique** every external reviewer flagged (LLM-as-judge circularity): the Red Queen makes fitness mean
"survived an adversary actively evolving to defeat it," not "a judge with shared priors approved." That same shift is
Granum's honest-impact answer to the strongest competitor (`colinh09/DietTrace`, whose deterministic ground truth is
a cleaner accuracy story than a static judge composite).

**Framing principle:** the hard algorithmic work is already built and unit-tested. This effort is **wiring + live-runs
+ two small frontend components + one held-out eval**, reusing 8 existing modules. It is depth-activation, not invention.

## 2. Background — what's already built vs. dormant (verified 2026-06-03)

| Mechanism | Code (built + unit-tested) | Live-run? | Demoed? |
|---|---|---|---|
| Germinal cycle | `center/cycle.py`, `center/evolution.py` | ✅ | ✅ |
| Negative selection | `center/negative_selection.py` | ✅ | ✅ |
| **Red Queen co-evolution** | `center/coevolution.py` (`CoEvolutionDriver.round()`), `center/triangular_tournament.py`, `adversary/payer_agent.py`, `adversary/payer_persona.py` (`SEEDED_PERSONAS`), `center/defensibility_judge.py` | ❌ never | ❌ |
| **Cross-cell transfer** | `transfer/embedding.py` (`CellEmbedder`), `transfer/trial.py` (`TransferTrialHarness`, promote gate p<0.05 & lift≥1.0) | ❌ | ❌ |
| **Immune memory** | `center/immune_memory.py` (reactivate champion on 2nd consecutive extinction) | ❌ | ❌ |
| **Antigen drift** | `center/antigen_drift.py` (distribution-shift detector) | ❌ | ❌ |

`center/driver.py` already orchestrates immune-memory + antigen-drift across cells but has no live CLI (`cycle-all`
is a stub). The frontend `web/components/CoEvolutionDualTree.tsx` exists; `GET /api/cells/{cell}/coevolution` already
serves `{cell}_coevolution.json` the moment that file exists — both wired to nothing.

## 3. Acceptance criteria (evidence-based "done")

1. **Red Queen live:** `granum coevolve` runs on real Phoenix + Gemini, emits a real `{cell}_coevolution.json`
   matching `web/lib/types.ts` `CoEvolutionState`, and `CoEvolutionDualTree` renders real writer + payer lineages
   with apoptosis visible on **both** populations.
2. **Memory + drift live:** the multi-cell driver runs live and captures ≥1 real immune-memory reactivation AND
   ≥1 real antigen-drift fire, surfaced in the UI as discrete events.
3. **Transfer live:** cross-cell transfer runs live and renders ≥1 promoted edge (gate: p<0.05 & lift≥1.0), OR
   honestly shows "no significant transfer detected X→Y" (a credible scientific result, not a failure).
4. **Honesty hardening:** a held-out adversarial eval (champion vs payer personas it never trained against) yields a
   labeled "held-out defensibility" number; impact framing tightened to KFF Medicare-Advantage 2024 sourcing
   (11.5% appealed, ~80% overturned), keeping the "appeal fitness" relabel.
5. **Quality gates:** full test suite + ruff + mypy green (new runners/endpoints covered by tests, TDD); E2E
   Playwright-verified against real data behind `NEXT_PUBLIC_USE_REAL_API`; deployed (Cloud Run + Vercel); demo
   re-cut showing Phoenix traces on camera.

## 4. Design — components

**New:**
- `center/coevolution_run.py` — `CoEvolutionRun` runner mirroring `GenerationalEvolution`: chain
  `CoEvolutionDriver.round()` ×N, accumulate writer + payer lineage nodes (generation, parentId from the mutant
  naming convention, fitness from defensibility composite, status from a final Phoenix sweep), and `to_payload()`
  → `CoEvolutionState` (`{cell, writers: BCellStrategy[], payers: BCellStrategy[]}`).
- Payer seeding in `data/seeds.py` — `seed_payers` / `reset_payers` from `SEEDED_PERSONAS`, analog to existing
  `seed_cell` / `reset_cell` (the inline re-seed logic in `coevolution.py`'s adversary-reset is the reference shape).
- CLI commands in `cli.py`: `coevolve` (mirror `evolve`), `drive` (live multi-cell driver, replacing the
  `cycle-all` stub), `transfer` (run the transfer harness).
- API endpoints in `web/api.py`: `GET /api/system` (immune events: memory reactivations + drift fires) and
  `GET /api/transfers` (promoted/attempted transfer edges). `/api/cells/{cell}/coevolution` already exists.
- Held-out eval module — 2–3 payer personas excluded from the training pool; evaluate final champion against them.
- Frontend: a compact "immune events" timeline component and a cross-cell transfer-edge component (small graph).

**Modified:** `cli.py`, `web/api.py`, `data/seeds.py`, frontend (light up `CoEvolutionDualTree`, add the two
components above, surface the held-out number + KFF sourcing), `api_data/` curated payloads.

**Reused unchanged (built + tested):** `CoEvolutionDriver`, `TriangularTournament`, `PayerAgent`,
`DefensibilityJudge`, `ImmuneMemory`, `AntigenDrift`, `TransferTrialHarness`, `CellEmbedder`.

## 5. Phased plan with failure modes

### E1 — Red Queen live (the moat-maker; do first)
Build `CoEvolutionRun` + payer seeding + `granum coevolve --cell --rounds --reset`. Run live at max quality
(Gemini 3.1 Pro both populations, 3 writers × 3 payers, 8–10 rounds, run several, curate cleanest honest arc).
Persist `runs/cell_payloads/{cell}_coevolution.json`; bake curated into `api_data/`; light up the dual-tree viz.
- **FM-a cost/latency** O(writers×payers×rounds) judge calls → async-concurrent the tournament; temp 0.
- **FM-b Red Queen oscillation/noise** → run several, curate the cleanest.
- **FM-c payload shape drift** vs `types.ts` → validate `to_payload()` against the type on the FIRST run, not last.
- **FM-d defensibility-judge inconsistency** → temp 0, reuse the existing rubric pattern.

### E2 — Immune memory + antigen drift live
Make `driver.py` runnable via `granum drive`; run a denial sequence engineered to genuinely trigger a drift fire
and an extinction→memory-reactivation (mechanism real, scenario curated). Emit `runs/system_events.json` →
`/api/system` → an "immune events" timeline panel.
- **FM-a** hard to naturally trigger extinction/drift in a short window → script the denial sequence so the *real*
  mechanisms fire; never fake the event, only arrange the conditions.
- **FM-b** UI scope creep → ship a simple chronological timeline, not a heavy new visualization.

### E3 — Cross-cell transfer live
Live-run 1–2 additional cells (donors/recipients), run `TransferTrialHarness`, emit `runs/transfers.json` →
`/api/transfers` → a small cross-cell edge graph.
- **FM-a** needs multiple live cells (cost/time — accepted under max-quality).
- **FM-b** statistical gate may promote nothing → show the honest negative result.
- **FM-c** one new frontend component → keep minimal.

### E4 — Honesty hardening
Build 2–3 held-out payer personas; evaluate the final champion against them → labeled "held-out defensibility"
(generalization, harder to game; still judge-rated, label honestly). Tighten impact to KFF MA 2024 sourcing.
- **FM-a** held-out personas must be genuinely distinct or the number is meaningless.
- **FM-b** don't overclaim — the held-out number is still judge-rated; label it as such.

### E5 — Integrate, verify, deploy, demo (throughout + end)
TDD the new runners/endpoints; full suite + ruff + mypy; supervised Cloud Run + Vercel (the existing Phase D, now
carrying the richer payload); re-cut the demo around the full immune system **with Phoenix traces on screen** (the
named "tracing" criterion + the AgentGov "show it live" lesson); update `docs/submission.md`.

## 6. Data flow (unchanged, proven)

Live runs (Phoenix prompt registry + datasets + Gemini judge) → JSON run artifacts → curated into `api_data/` →
FastAPI serves them statically → Next.js renders behind `NEXT_PUBLIC_USE_REAL_API`. No live Phoenix/MCP dependency
at request time, so Cloud Run stays lean — identical to the already-shipped single-population loop.

## 7. Testing & verification

- TDD each new unit (runner, seeding, endpoints, held-out eval) before wiring.
- Keep the existing 182 tests green; add coverage for the new runners + endpoints.
- E2E: Playwright the local frontend against the live API showing real co-evolution + transfer + immune-events data.
- Verification gate before any "done" claim: inspect the real artifact, run the suite, confirm the UI renders real
  data — agent/test summaries are not evidence until inspected.

## 8. Sequencing & effort

E1 first (highest leverage). E4's held-out eval rides on E1's co-evolution run. E2 and E3 are depth multipliers.
E5 runs throughout and closes. The critical path is wiring + curated live-runs, not new algorithms — feasible inside
the 8-day window at max quality.

## 9. Bug protocol

Any live-run breakage → reproduce → root-cause against the REAL MCP/Gemini response (capture-then-code; the Phoenix
schema-audit lesson), not assumptions → targeted fix → re-verify the original failing case → check regressions →
only then proceed.

## 10. Out of scope (YAGNI)

No net-new mechanisms (the immune model is already chosen). No real payer/FHIR intake. No streaming inline eval.
No rename. No refactors unrelated to activation.
</content>
