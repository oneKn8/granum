# Granum

> An immune system for medical appeals.

When your insurance denies medically necessary care, your physician can appeal — and 83% of appeals succeed. But only 1 in 10 denials is ever appealed, because writing appeals is expensive: 12 hours per week of physician time, in a country where physicians cost $300/hour. **The math kills the appeal before it's ever written.**

Granum is an agent that drafts those appeals. It doesn't ship one fixed appeal template — it maintains an evolving population of appeal strategies, one per (payer × diagnosis) pair, that compete on real outcomes. Strategies that win against denials survive and mutate. Strategies that lose are **permanently deleted**.

The mechanism is borrowed from immunology: [germinal-center affinity maturation](https://en.wikipedia.org/wiki/Affinity_maturation). Your B-cells evolve antibodies the same way — somatic hypermutation, antigen-driven selection, and apoptosis of low-affinity variants. Granum applies it to prompts.

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — **Arize Phoenix track**.

> **Live:** *(deploy URL TBD before submission)*
> **Demo video:** *(YouTube link TBD)*

---

## How it works

Each (payer × diagnosis) cell in Granum holds a small population of "B-cell" appeal strategies. A strategy is a system prompt + an evidence template + a tool-use pattern.

When a new denial arrives:

1. **Selection** — top-N surviving strategies in the matching cell each generate a candidate appeal.
2. **Tournament** — every candidate is scored against the gold dataset of prior overturned appeals, using LLM-as-judge with structured English feedback (no scalar rewards).
3. **Submission** — the winning candidate's appeal is dispatched.
4. **Outcome ingestion** — when the payer responds (overturn / uphold / partial), the result is written back to Phoenix via `add-dataset-examples`. The dataset is the antigen.
5. **Apoptosis** — losing strategies' prompt versions are **permanently removed** from the Phoenix prompt registry. No revert. No "archive." Gone.
6. **Mutation** — surviving strategies generate small mutations via `upsert-prompt` — swap one citation, change one clinical guideline reference, reframe one paragraph. `add-prompt-version-tag` marks new mutants `experimental`; promotion to `production` requires beating the current champion on the golden dataset.

Phoenix renders the germinal-center lineage tree: surviving lineages branch, extinct ones grey out, fitness curves climb generation over generation.

---

## Why this exists

Three things converged:

- **A real, unfilled pain.** Existing prior-auth automation startups serve *payers* — that's where the budget is. Nobody serves the *denied* side. The AMA documents the gap: 12 hrs/wk per physician, 83% appeal win rate, 10% file rate, 78% of patients abandoning treatments. That's the gap.
- **A mechanism nobody has applied to agents.** Every "self-improving agent" published today is a hierarchical supervisor pattern — meta agent watches target agent. Affinity maturation is peer evolutionary competition with permanent deletion. Different shape. Different scaling story.
- **A platform that wants this.** Arize Phoenix's MCP server exposes `add-dataset-examples`, `upsert-prompt`, `add-prompt-version-tag`, and trace-introspection tools that chain end-to-end into a data flywheel. No published demo has wired them up. We're wiring them up.

---

## What you'll see in the demo

The 3-minute walkthrough opens with a real Aetna denial of a medically necessary cardiac procedure. Three mutant appeal strategies generate three candidate appeals. LLM-as-judge scores each against twelve prior overturned Aetna+cardiac appeals from the gold dataset. The winner is selected. The two losing strategies' prompt versions are deleted — the lineage tree nodes turn grey.

Six weeks of synthetic outcomes fast-forward. The lineage tree branches and prunes. The fitness curve climbs from 41% overturn rate (vanilla baseline) to 79% (Gen 8). A side-by-side prompt diff shows what the agent learned about Aetna's specific clinical-necessity language between generation 1 and generation 8.

The Phoenix UI is the demo — not a wrapper. The lineage tree, the prompt diffs, the experiment runs, the dataset growth — all viewed through Arize's own surfaces.

---

## Stack

- **Agent runtime** — [Google ADK](https://google.github.io/adk-docs/) (Python)
- **Reasoning** — Gemini 3 Pro (Vertex AI / Gemini Enterprise Agent Platform)
- **Observability + evolution backbone** — [Arize Phoenix](https://arize.com/docs/phoenix), [`@arizeai/phoenix-mcp`](https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp)
- **Hosting** — Cloud Run (us-central1), Cloud Scheduler for periodic mutation rounds
- **State** — Phoenix prompt registry + datasets (the population lives in Phoenix)
- **Frontend** — Thin Next.js layer over the Phoenix lineage view; baseline-ui + a11y + motion + metadata polish pipeline applied
- **Synthetic denial data** — public CMS appeal-rate datasets + de-identified case patterns published by AMA and PIE.gov

---

## Architecture

```
                +-----------------------+
                |   Denial intake       |  (synthetic in demo;
                |   API + parser        |   real PA in v0.2)
                +-----------+-----------+
                            |
                            v
       +---------------------------------------------+
       |        Germinal Center  (per cell)          |
       |   payer × diagnosis  -->  B-cell population |
       |                                             |
       |   1. Selection (top-N candidates)           |
       |   2. Tournament (LLM-as-judge vs. gold ds)  |
       |   3. Submission of winner                   |
       |   4. Outcome write-back (antigen update)    |
       |   5. Apoptosis  (permanent delete)          |
       |   6. Mutation (upsert-prompt + tag)         |
       +-----------+---------------------------------+
                   |
                   |  every tool call, every span
                   v
              +---------+
              | Phoenix |  prompt registry, datasets,
              |   MCP   |  experiments, traces, evals
              +---------+
                   |
                   v
              Lineage tree (UI) — survivors branch, losers grey out
```

There is **one** agent. There is no target agent, no supervisor, no meta-watcher. The agent is the germinal center — it generates, competes, mutates, and prunes its own population.

---

## What makes Granum different

Six other entries on the Arize track ([mender-agent](https://github.com/mattspaulding/mender-agent), [agent-sre](https://github.com/OJ-IRO/agent-sre), [tracepilot](https://github.com/bullyopswork/tracepilot), [flightcheck](https://github.com/divergent99/flightcheck), [axon](https://github.com/colinh09/axon), [Aegis-1](https://github.com/Arham-Begani/Aegis-1)) all implement the same supervisor architecture: a meta-agent watches a target agent and patches it. They are excellent. They are also the saturated cluster.

Granum is structurally inverted:

| Dimension | Supervisor pattern (the field) | Granum |
|---|---|---|
| Topology | Meta-agent + target agent | Single agent, evolutionary peer competition |
| Update model | LLM-as-judge → patch → revert if bad | Permanent deletion of losers |
| Version history | All versions retained | Apoptosis — losing versions removed forever |
| Layer | Horizontal infrastructure | Vertical product (medical appeals) |
| Self-improvement primitive | Diagnose → fix | Mutate → compete → prune |
| Story | "Your agents have bugs; we fix them" | "Patients are denied care; we evolve appeals that win" |

---

## Status (hackathon timeline 2026-05-27 → 2026-06-11)

| Phase | Days | Status |
|---|---|---|
| P0 Foundation (repo, license, GCP creds, smoke tests) | 1–2 | _pending_ |
| P1 Germinal Loop (single B-cell tournament, apoptosis) | 3–5 | _pending_ |
| P2 Lineage (multi-gen evolution, lineage tree viz) | 6–8 | _pending_ |
| P3 Outcome Loop (dataset writeback, closed cycle) | 9–10 | _pending_ |
| P4 Polish (UI polish pipeline, demo recording) | 11–12 | _pending_ |
| P5 Submit (YouTube, Devpost form, verification) | 13–14 | _pending_ |

---

## Quickstart

```bash
# Prerequisites
brew install --cask google-cloud-sdk
curl -LsSf https://astral.sh/uv/install.sh | sh

# Auth + project
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>

# Phoenix Cloud (free tier) — get an API key at https://app.phoenix.arize.com
echo "PHOENIX_API_KEY=..." >> .env
echo "PHOENIX_COLLECTOR_ENDPOINT=..." >> .env

# Install + smoke
uv sync
uv run granum doctor
uv run granum seed --cell aetna_cardiac --gen 0
uv run granum cycle --cell aetna_cardiac
```

---

## Project layout (planned)

```
granum/
├── src/granum/
│   ├── agent.py             # ADK agent — single LlmAgent
│   ├── cli.py               # commands (doctor, seed, cycle, demo)
│   ├── center/              # germinal center logic
│   │   ├── selection.py     # top-N candidate selection
│   │   ├── tournament.py    # LLM-as-judge competition
│   │   ├── mutation.py      # upsert-prompt mutation operators
│   │   └── apoptosis.py     # permanent prompt deletion
│   ├── tools/               # Phoenix MCP wrappers
│   ├── data/                # synthetic denial generators, gold dataset loader
│   └── web/                 # Next.js demo + Phoenix lineage tree overlay
├── infra/                   # Cloud Run + Scheduler config
├── data/
│   ├── synthetic-denials/   # CMS-derived denial fixtures
│   └── gold-appeals/        # historical overturned appeals (synthetic)
├── docs/
│   ├── PRODUCT.md           # what Granum is, who it's for, why
│   ├── architecture.md
│   ├── biology-mapping.md   # immunology → prompt-evolution mapping
│   └── demo-script.md
└── LICENSE                  # Apache-2.0
```

---

## License

Apache-2.0 — see [`LICENSE`](LICENSE).

---

## Acknowledgements

- Arize team for Phoenix and the MCP server, particularly the under-publicized prompt-registry + dataset-writeback tools that make this loop possible.
- Victora & Mesin, *Visualizing antibody affinity maturation in germinal centers* (Science, 2016) — the immunology source.
- AMA *Prior Authorization Physician Survey* — the stats that proved the gap.
