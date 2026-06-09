# Granum

> An immune system for medical appeals.

When your insurance denies medically necessary care, your physician can appeal, and 83% of appeals succeed. But only 1 in 10 denials is ever appealed, because writing appeals is expensive: 12 hours per week of physician time, in a country where physicians cost $300/hour. **The math kills the appeal before it's ever written.**

Granum is an agent that drafts those appeals. It doesn't ship one fixed template. It maintains an evolving population of appeal strategies, one per (payer × diagnosis) cell, that compete on judge-scored outcomes. Strategies that win against denials survive and mutate. Strategies that lose are retired for good. The mechanism is borrowed from immunology: [germinal-center affinity maturation](https://en.wikipedia.org/wiki/Affinity_maturation). That is somatic hypermutation, antigen-driven selection, and apoptosis of low-affinity variants. Granum applies it to prompts.

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/), **Arize Phoenix track**.

---

## Live

- **Frontend:** https://granum-oneknights-projects.vercel.app (Vercel, Next.js 15)
- **API:** https://granum-api-lpgmo76lta-uc.a.run.app (Cloud Run, GCP project `granum-2026`)
  - `GET /api/cells`: every evolved cell and its meta
  - `GET /api/cells/{cell}`: one cell's full strategy population + lineage
  - `GET /api/cells/{cell}/coevolution`: Red Queen writer-vs-payer dual lineage
  - `GET /api/transfers`: cross-cell strategy transfer results

---

## What's shipped

Two cells have evolved end-to-end on live Phoenix + Vertex Gemini, plus one cross-cell transfer:

| Cell | Judge-rated overturn likelihood | Generations | Strategies apoptosed |
|---|---|---|---|
| `aetna_cardiac` | 0.40 → 0.98 | 10 | 18 |
| `united_oncology` | 0.62 → 0.98 | 10 | 18 |

**Cross-cell transfer.** Granum tests whether a champion strategy from one cell helps another. `united_oncology` → `aetna_cardiac` was **promoted**: +1.92 composite on the 0–10 judge scale, p = 0.024, 5/5 trials pass negative selection. The reverse, `aetna_cardiac` → `united_oncology`, was **rejected**. The Aetna champion is too citation-rigid to generalize, and all 5 trials failed negative selection. The asymmetry is honest: transfer works when a strategy is general enough to survive a new antigen, and not otherwise.

256 tests pass. `ruff` and `mypy` are clean.

---

## How it works

Each (payer × diagnosis) cell holds a small population of "B-cell" appeal strategies. A strategy is a system prompt + an evidence template + a tool-use pattern. Each generation:

1. **Selection.** Top-K surviving strategies in the cell each draft a candidate appeal.
2. **Negative selection.** A thymic-style guard pre-kills any draft with a hallucinated citation or unsupported clinical claim, before scoring.
3. **Tournament.** Every candidate is scored against a gold dataset of prior overturned appeals using an LLM-as-judge on a 5-axis rubric, producing structured English feedback (no scalar rewards).
4. **Submission.** The winning appeal is dispatched (mocked endpoint in this build).
5. **Outcome ingestion.** The result is written back to a Phoenix dataset via `add-dataset-examples`. The dataset is the antigen.
6. **Apoptosis.** Losing strategies have their `production` tag stripped and a `tombstoned` tag added. Phoenix prompt versions are immutable by design, so this is functional apoptosis: the strategy is structurally ineligible for future selection or mutation, while the full audit lineage is preserved.
7. **Mutation.** Survivors generate small mutations via `upsert-prompt`: swap one citation, change one clinical guideline reference, reframe one paragraph. New mutants are tagged `experimental`; promotion to `production` requires beating the current champion.

The frontend renders the germinal-center lineage tree: surviving lineages branch, extinct ones grey out, the fitness curve climbs generation over generation.

---

## The Phoenix self-improvement loop

Phoenix is not a dashboard bolted on after the fact. It is the substrate the agent runs on, and it is what closes the self-improvement loop.

- **The population lives in Phoenix.** `list-prompts` filtered to `production`-tagged versions in a cell *is* the current B-cell population. There is no separate strategy database.
- **Every run emits rich spans.** Each generation writes first-class span attributes: `granum.generation`, `granum.winner_fitness`, `granum.apoptosis_count`, `granum.mutation_notes`, `granum.judge_critique`. The story is queryable telemetry, not a log line.
- **The agent reads its own telemetry back.** Before mutating, the agent calls the Phoenix MCP `get-spans` tool to pull its own prior-generation spans, and the mutator optimizes against the weaknesses its observability data keeps surfacing. This is the Arize bonus criterion (an agent that uses its own observability data to improve over time), closed for real and surfaced in the UI as the **SelfImprovementLoop** panel.
- **Mutation, promotion, and apoptosis are all Phoenix calls.** `upsert-prompt` births a variant, `add-prompt-version-tag` promotes or tombstones it. If Phoenix disappeared, Granum would have no state.

---

## Stack

- **Reasoning model:** Gemini 3.1 Pro (`gemini-3.1-pro-preview`) on Vertex AI; `gemini-3.5-flash` for high-volume mutation calls
- **Agent runtime:** [Google ADK](https://google.github.io/adk-docs/) (Python 3.12, uv-managed)
- **Observability + evolution backbone:** [Arize Phoenix](https://arize.com/docs/phoenix) Cloud + [`@arizeai/phoenix-mcp`](https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp), with Phoenix REST for tag mutation
- **API:** FastAPI on Google Cloud Run (us-central1)
- **Frontend:** Next.js 15 (App Router) + React 19 + Tailwind on Vercel; D3 lineage tree, Recharts fitness curves
- **State:** Phoenix prompt registry + datasets (the population lives in Phoenix)
- **Data:** synthetic, grounded in real CPT/HCPCS/ICD-10 codes, real payer-policy IDs, and real clinical-guideline citations

---

## Quickstart

```bash
# Prerequisites: gcloud SDK + uv (backend), pnpm (frontend)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Auth + project
gcloud auth login
gcloud auth application-default login
gcloud config set project granum-2026

# Env: copy the template and fill in your Phoenix key + GCP project
cp .env.example .env
# set PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT, GOOGLE_CLOUD_PROJECT

# Backend install + checks
uv sync
uv run granum doctor          # verify env vars, Vertex access, Phoenix auth
uv run granum version

# Run one live generation, or a full multi-generation evolution
set -a; source .env; set +a
uv run granum cycle --cell aetna_cardiac
uv run granum evolve --cell aetna_cardiac --generations 10 --survival-count 3 --reset

# Red Queen co-evolution (writer population vs. adversarial payer population)
uv run granum coevolve --cell aetna_cardiac --rounds 8

# Frontend
cd web && pnpm install && pnpm dev
```

CLI verbs: `doctor`, `version`, `cycle`, `evolve`, `coevolve`. Cell seeding is handled by `scripts/seed_cell.py`.

---

## Project layout

```
granum/
├── src/granum/
│   ├── cli.py            # CLI: doctor, version, cycle, evolve, coevolve
│   ├── center/           # germinal center: cycle, evolution, tournament,
│   │                     #   mutation, negative selection, judge, co-evolution,
│   │                     #   immune memory, antigen drift, observability
│   ├── adversary/        # Red Queen payer agents + personas
│   ├── transfer/         # cross-cell embedding + transfer-trial harness
│   ├── tools/            # Phoenix MCP + Gemini client seams
│   ├── data/             # denial generation, gold-appeal loader, cell seeds
│   └── web/              # FastAPI app serving the cell payloads
├── web/                  # Next.js 15 frontend (App Router, D3, Recharts)
├── data/                 # 5 cells: denial templates, gold appeals, citations,
│                         #   payer personas, judge rubrics
├── api_data/             # baked cell payloads served by the API
├── scripts/              # seed_cell.py, demo + voiceover tooling, smoke tests
├── infra/                # Cloud Run deploy
├── docs/                 # PRODUCT, submission, demo-script, biology-mapping, specs
└── LICENSE               # Apache-2.0
```

---

## License

Apache-2.0. See [`LICENSE`](LICENSE). Copyright 2026 Shifat Islam Santo.

---

## Acknowledgements

- Arize team for Phoenix and the MCP server, particularly the prompt-registry + dataset-writeback tools that make this loop possible.
- Victora & Mesin, *Visualizing antibody affinity maturation in germinal centers* (Science, 2016), the immunology source.
- AMA *Prior Authorization Physician Survey*, the stats that proved the gap.
