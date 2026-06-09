# Demo guide — what to SHOW in Phoenix (this is where the Arize track is won)

The Arize rubric names **"meaningful use of tracing"** and gives a **bonus for agents
that use their own observability data to improve over time.** Judges built Phoenix —
they will open it. The biggest scoring lever is not more backend; it's putting the
**Phoenix dashboard on screen** so the loop is undeniable. AgentGov lost the
presentation half by demoing via CLI. Do not repeat that.

Project in Phoenix: `granum` at `https://app.phoenix.arize.com/s/<account>` (see `.env`
`PHOENIX_COLLECTOR_ENDPOINT`). A clean, recent run is already traced there.

---

## The 4 Phoenix views to record (≈40s of the 3-min video) and the exact narration

### 1. The germinal-cycle trace — "the loop is real, and it climbs"
Phoenix → **Traces** → filter span name `granum.cycle.aetna_cardiac`. Open one generation's
span → **Attributes**. Every generation carries the story as first-class span data:

| Attribute | What it shows |
|---|---|
| `granum.generation` | which generation |
| `granum.winner_fitness` | the champion's judge composite (0–10) — **climbs across generations** |
| `granum.winner_id` | the surviving lineage |
| `granum.apoptosis_count` / `granum.apoptosis_ids` | strategies killed this generation (functional apoptosis) |
| `granum.mutation_notes` | what the feedback-directed mutator changed (real text, e.g. *"Added verbatim policy quotes, ACC/AHA, and appeal level"*) |
| `granum.judge_critique` | the English critique the next generation learns from |
| `granum.negative_selection_rejected` | hallucinated-citation strategies killed pre-tournament |

> **Narration:** *"Each generation of appeal strategies is a span in Phoenix. Fitness
> climbs 0.40 → 0.98, losers are apoptosed, and the judge's English critique is
> recorded as telemetry — not a number, English feedback, exactly Arize's prompt-learning thesis."*

### 2. The bonus loop — "it improves from its OWN observability data" [key beat]
Filter span name `granum.cycle.read_self_observability`. Open a gen-2+ span → attribute
`granum.observability_readback_generations` (grows 1 → 2 → 3). This span sits **before**
the mutation each generation.

> **Narration:** *"Before mutating, the agent calls Phoenix MCP `get-spans` to read its OWN
> prior-generation telemetry back, and the mutator optimizes against the weaknesses its
> observability data keeps surfacing. That's the Arize bonus criterion — using its own
> observability data to improve over time — closed for real, visible right here in the trace."*

This is the single most important 8 seconds of the video. Hold on it.

### 3. The prompt registry — "Phoenix IS the genome / the apoptosis ledger"
Phoenix → **Prompts**. Filter to `aetna_cardiac/`. Show:
- prompt **versions** = the B-cell lineage (gen 0 seed → mutants), each a real prompt version.
- **tags**: `production` = alive/champion, the apoptosed losers stripped of production (tombstoned ledger preserved — audit history, never deleted).

> **Narration:** *"We don't bolt observability on — Phoenix's prompt registry IS the genome.
> Versions are lineage, tags are life and death."*

### 4. The outcomes dataset — "the closed loop"
Phoenix → **Datasets** → `granum/aetna_cardiac/outcomes`. Each generation writes its
outcome (winner, composite, critique). Pair with the lineage tree in our own UI.

### 5. The second cell + cross-cell transfer — "it generalizes, honestly"
`united_oncology` evolved the same way (0.62 → 0.98 over 10 generations) and has its own
spans, prompt lineage, and outcomes dataset. Then show transfer: in our UI the
`united_oncology` champion transferred into `aetna_cardiac` was promoted (+0.19 lift on the
normalized scale, p = 0.024), while the reverse was rejected.

> **Narration:** *"The same loop evolved a second cell, oncology, 0.62 to 0.98. And one cell's
> champion can transfer to another: united-to-aetna gave a significant lift, p equals zero
> point zero two four, so it was promoted. The reverse was rejected, because that champion was
> too citation-rigid to generalize. The asymmetry is the honest result."*

---

## The on-camera live-grow moment (our UI + Phoenix side-by-side)
Run the loop LIVE so the tree grows on camera while Phoenix fills with spans:

```bash
# terminal 1 — API serving the live dir
GRANUM_DATA_DIR=runs/cell_payloads \
  env -u PYTHONPATH uv run uvicorn granum.web.api:app --host 0.0.0.0 --port 8090
# terminal 2 — the frontend pointed at :8090 (FE owns web/)
# terminal 3 — the live run (rewrites runs/cell_payloads/aetna_cardiac.json each generation)
set -a; source .env; set +a
GEMINI_MODEL=gemini-3.5-flash GRANUM_MUTATOR_MODEL=gemini-3.1-pro-preview \
GRANUM_DATA_DIR=runs/cell_payloads \
  env -u PYTHONPATH uv run granum evolve --cell aetna_cardiac --generations 10 \
    --survival-count 3 --reset
```
The lineage tree grows + fitness curve climbs in our UI (no restart), while the same run
streams rich spans into Phoenix. Show both.

---

## Rubric mapping (say these words)
- **Technical implementation (tie-break #1):** germinal-center evolution + Red Queen co-evolution + elitist top-K selection, on ADK + Gemini 3.1 Pro + Cloud Run.
- **Tracing + MCP:** OpenInference spans carrying the story (view 1) + Phoenix MCP as the prompt-registry/dataset substrate (views 3–4) + LLM-as-judge.
- **Self-improvement loop + BONUS:** views 1 & 2 — visible climb, and improvement driven by its own Phoenix telemetry.
- **Impact:** denied medical care. AMA: physicians spend 12 hrs/wk on prior-auth; 83% of appeals overturn but only ~10% are filed. Label fitness honestly as judge-rated appeal quality on a synthetic-but-grounded gold set (real Aetna CPB + ACC/AHA citations, validated by negative selection).
