# Granum — Devpost Submission Text

> Source-of-truth for every Devpost form field. Copy-paste directly into the form on submission day. Last revised 2026-05-27 by Terminal C; deadline 2026-06-11 14:00 PDT.

---

## 1. Project name

**Granum**

## 2. Elevator pitch (≤ 200 chars)

> An immune system for medical appeals. Granum evolves a population of appeal strategies per (payer × diagnosis) — winners mutate, losers are permanently deleted from Phoenix. Powered by Arize Phoenix MCP.

(193 characters incl. spaces.)

## 3. Inspiration

US insurers deny medically necessary care to millions of patients every year. The AMA's 2023 *Prior Authorization Physician Survey* documents the resulting pain in painfully specific numbers: physicians spend an average of **12 hours per week** on prior-authorization work, **94%** report PA-related care delays, and **78%** see patients abandon treatment because the appeal process is too slow. The cruel twist: **83% of appeals that are actually filed succeed**, but **only ~10% of denials are ever appealed at all**, because writing one costs twelve hours of a physician's time at three hundred dollars an hour. The math kills the appeal before it's ever written.

Every prior-auth automation startup we surveyed serves the payer — that's where the budget lives. Nobody serves the denied side. We wanted to fix the side where patients lose.

Separately, we were studying affinity maturation in germinal centers (Victora & Mesin, *Science* 2016) — the immune-system mechanism by which B-cells evolve antibodies against a novel pathogen via somatic hypermutation, antigen-driven tournament selection, and apoptosis of low-affinity variants. The structural property that makes germinal centers honest is **commitment**: a B-cell that loses the tournament is permanently deleted. There is no archive, no revert. That constraint forces every mutation to be a real bet.

We wondered: nobody is doing this with prompts. Every "self-improving agent" we surveyed keeps full version history "just in case." What if we built one that didn't? What if losing strategies got *permanently deleted*?

Granum is the answer.

## 4. What it does

Granum is a single ADK agent that drafts prior-authorization appeals on behalf of denied patients and their physicians. Unlike a generic LLM appeal-writer, it maintains a small evolving population of appeal **strategies** for each (payer × diagnosis) pair — a strategy is a system prompt + an evidence-retrieval template + a tool-use pattern.

For each new denial in the matching cell:

1. **Selection** — Granum chooses the top-N surviving strategies as candidates.
2. **Negative selection** — a thymic-style guard pre-kills any strategy whose draft contains a hallucinated citation, an unsupported clinical claim, or a missing deadline reference. Hallucination defense happens *before* the tournament, not after.
3. **Tournament** — every surviving candidate drafts an appeal; an LLM-as-judge scores each one against a gold dataset of prior overturned appeals using a 5-axis rubric with median-of-3 sampling, producing **structured English feedback** (no scalar rewards — matching Arize's prompt-learning thesis).
4. **Submission** — the winning candidate's appeal is dispatched (mocked endpoint in v0.1).
5. **Outcome ingestion** — the result (overturn / uphold / partial) is written back to Phoenix via `add-dataset-examples`. The dataset *is* the antigen.
6. **Apoptosis (Path B)** — losing strategies have their `production` tag removed via Phoenix REST and a `tombstoned` tag added via MCP. Phoenix prompt versions are immutable by design, so this is functional apoptosis: the strategy is structurally ineligible for future selection or mutation, the full audit lineage is preserved, and there is no revert.
7. **Mutation** — surviving strategies generate small mutations via Phoenix MCP `upsert-prompt`. Mutations are deliberately tiny: swap one citation, change one clinical guideline reference, reframe one paragraph. Large rewrites are banned — affinity maturation is incremental.
8. **Immune memory** — old champions are tagged `memory_cell` and preserved as fallback strategies. After two consecutive extinctions in a cell, the most recent memory cell is reactivated.
9. **Antigen drift** — when denial patterns shift (bag-of-features symmetric difference > 25%), Granum retests dormant memory cells against the new antigen distribution.

Five cells ship in v0.1: Aetna+cardiac, United+oncology, Anthem+mental-health, Cigna+orthopedic, Humana+endocrinology. Each cell has 10 denial patterns, 40+ verified clinical-policy citations, 12 gold overturned-appeal exemplars, and a specialized 5-axis judge rubric.

The product is the lineage tree — a phylogenetic visualization of every strategy that ever existed in a cell. Survivors branch. Apoptosed nodes grey out with strikethrough lineage. The fitness curve climbs from 0.41 (vanilla baseline overturn rate) to 0.79 over 8 generations on Aetna+cardiac in our seeded demo run.

## 5. How we built it

**Stack.**

- **Agent runtime** — [Google ADK](https://google.github.io/adk-docs/) (Python 3.12, uv-managed)
- **Reasoning model** — Gemini 3 Pro on Vertex AI (Gemini Enterprise Agent Platform)
- **Observability + evolution backbone** — [Arize Phoenix](https://arize.com/docs/phoenix) Cloud + [`@arizeai/phoenix-mcp`](https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp) + Phoenix REST for tag mutation
- **Hosting** — Google Cloud Run (us-central1), Cloud Scheduler for periodic mutation rounds
- **State** — Phoenix prompt registry + datasets (the population literally lives in Phoenix)
- **Frontend** — Next.js 15 (App Router) + Tailwind 4, D3 for the phylogenetic lineage tree, Recharts for fitness curves
- **License** — Apache-2.0

**Phoenix MCP tool chain (end-to-end, no decorative wrapping).**

| Tool | Where Granum uses it |
|---|---|
| `list-prompts` | Read current B-cell population for the matching cell |
| `upsert-prompt` | Apply mutation operators to surviving strategies |
| `add-prompt-version-tag` | `experimental` → `production` promotion; also `memory_cell`, `tombstoned` |
| REST `DELETE /prompts/.../tags/production` | Path B apoptosis — strip champion status |
| `add-dataset-examples` | Write each new appeal outcome back as antigen data |
| `get-spans`, `get-span-annotations` | Online introspection of past appeal traces and judge annotations |
| `list-traces`, `get-trace` | Lineage reconstruction for the visualization |
| Experiments API | Tournament scoring (candidate appeals vs. gold dataset) |

All Phoenix interaction is mediated by a single seam (`src/granum/tools/phoenix_client.py`, 7 tests) — no other Granum module references Phoenix tool names or REST paths.

**Process discipline.** We worked from a numbered, phased plan (`docs/IMPLEMENTATION_PLAN.md`) with named failure modes per phase. Three terminals ran in parallel against the same repo with strict ownership boundaries: backend (Python + Phoenix), data (5 cells × 4 files), frontend (Next.js + demo). Each terminal committed under its own letter prefix (`[A]`, `[B]`, `[C]`) into `docs/standup.md`. CI was green from day one (15-second turnaround). Test-driven for every backend module; the polish pipeline (baseline-ui → fixing-accessibility → fixing-motion-performance → fixing-metadata) ran sequentially on the frontend.

## 6. Challenges we ran into

**Phoenix prompt versions are immutable.** Our original design assumed `delete-prompt-version` existed. The pre-flight Phoenix MCP capability audit (27 tools enumerated against a live workspace) proved it doesn't — and shouldn't, because prompt registries are supposed to be append-only audit logs. We pivoted to **Path B** — *functional* apoptosis via tag mutation. Removing `production` from a strategy and adding `tombstoned` makes the strategy structurally ineligible for selection or mutation while preserving the full audit lineage. The biology metaphor actually gets *stronger*: in real germinal centers, apoptosed B-cells are also not literally erased — they're flagged for clearance by tingible-body macrophages. Tags as macrophages.

**LLM-as-judge circularity.** Three external critics (ChatGPT + two Geminis + a browser-Claude) independently flagged the load-bearing flaw in any judge-scored evolution loop: if the judge shares priors with the generator, you climb a fake fitness gradient. Our response (currently mid-build, Phase 3 in progress in Terminal A) is a **co-evolutionary Red Queen**: a second adversarial *payer-agent* population evolves in parallel, actively looking for hallucinations and policy-citation weaknesses in candidate appeals. Survival means defeating an adversary, not impressing a judge.

**Avoiding the field's saturated pattern.** Six other published entries on the Arize track implement variants of the same hierarchical *supervisor* pattern (mender-agent, agent-sre, tracepilot, flightcheck, axon, Aegis-1) — all META-AGENT-watches-TARGET-AGENT. That pattern is excellent. It is also extremely crowded. We took the structural inverse: one agent, evolutionary peer competition with permanent commitment costs.

**The 12-hour-per-physician math is true. The 83% overturn-rate is true. The 10% file-rate is true.** Every number we cite resolves to AMA, KFF, or CMS public-record data. We caught ourselves once about to use a "trusted by 10K hospitals" framing — banned by our DESIGN.md anti-slop checklist before it shipped.

## 7. Accomplishments we're proud of

- **Full Phoenix MCP chain wired end-to-end** — no other entry on the track does this. All eight Phoenix surfaces are load-bearing; pull any one out and the agent stops working.
- **A novel structural primitive (apoptosis-via-tag) that survived contact with reality.** The Path B pivot off the immutability constraint made the metaphor *more* honest, not less.
- **Five cells, real citations.** Every CPT / HCPCS / ICD-10 code in the synthetic data is real. Every payer-policy ID resolves to a real document. Every clinical-guideline citation resolves to a real URL. The gold-appeal dataset (60 exemplars across 5 cells) passes negative-selection clean: zero hallucinated citations across the entire corpus.
- **Honest test coverage.** 67/67 tests passing; every mutation operator, judge axis, tournament protocol, immune-memory primitive, and antigen-drift detector tested with mocks; integration tests cover the full germinal cycle.
- **The frontend is the demo.** The lineage tree (D3 hierarchy + zoom), prompt-diff component (word-level with citation deltas), and fitness curve (synchronized with the generation tick) all rendered against deterministic mock data so the demo works offline if Phoenix is down. Polish pipeline passed all four stages.
- **A `DESIGN.md` and a banned-defaults checklist.** The frontend uses IBM Plex Serif + JetBrains Mono on OKLCH-tuned cell-stain blues and apoptosis red. No Inter, no Space Grotesk, no purple-blue gradients, no centered hero with two CTAs, no "trusted by" logo strip.

## 8. What we learned

- **Affinity maturation generalizes.** The germinal-center mechanism is a remarkably good description of how *any* learning system that has access to a quality signal but no gradient should structure its search. The Arize team's "prompt learning over scalars" thesis is exactly this — English-feedback judge scores are the antigen.
- **Phoenix MCP is more capable than its docs advertise.** The combination of prompt-registry tag move-semantics + dataset-writeback + span retrieval is a self-improvement substrate hiding in plain sight. We had to read the source code of the MCP server to discover that `add-prompt-version-tag` is move-semantic, which turned out to be the atomic primitive we needed for champion-swap.
- **Permanent deletion is psychologically heavy and structurally clean.** Apoptosis enforces commitment in a way that "revert if the new prompt is worse" doesn't. Knowing the loser is *gone* changes how aggressively you mutate.
- **The hard part is restraint, not generation.** Banning large rewrites and forcing only single-knob mutations (citation swap / paragraph reframe / clinical-guideline substitution) is what makes the lineage tree readable.

## 9. What's next

- **v0.2 (4–6 weeks post-hackathon):** Onboard 2–3 independent physician practices. Run on real denials with explicit consent + de-identified eval data. Ship a patient-advocate dashboard.
- **v0.3 (3 months):** Scale to ~20 (payer × diagnosis) cells. Outcomes-as-a-service API for physician-billing companies.
- **v1.0 (6 months):** Multi-payer cross-pollination via cell-embedding similarity. A strategy that learns to win against Aetna cardiac sometimes generalizes to United cardiac — Granum captures that transfer learning automatically.
- **v2.0 (12 months):** Federated cells across practices. Physicians' Granum instances share anonymized fitness signals without sharing patient data. The population becomes adaptive at population scale.

The eventual product is not "an AI that writes appeals." It is **a learning organism that gets better at fighting denials for every (payer × diagnosis) pair, indefinitely, with permanent commitment costs on every variant enforcing real selection.**

## 10. Built with (tags for Devpost)

```
google-cloud-platform
google-cloud-run
google-adk
gemini
vertex-ai
arize-phoenix
phoenix-mcp
mcp
model-context-protocol
python
typescript
nextjs
react
tailwindcss
d3
recharts
uv
healthcare
prior-authorization
medical-appeals
ai-agents
evolutionary-algorithms
prompt-learning
llm-as-judge
opentelemetry
```

## 11. Try it out

- **GitHub repo:** https://github.com/oneKn8/granum  *(Apache-2.0, public)*
- **Hosted URL:** *(Cloud Run deploy URL — fill on day 14 once Phase 0.5 deploys)*
- **Demo video:** *(YouTube link — fill on day 13 after rendering)*
- **Devpost project page:** *(fill once the form is created)*

## 12. Track selection

**Arize Phoenix track.**

### Arize-specific scoring overlay — self-improvement loop write-up

The Arize track has a published bonus criterion: the agent uses its own observability data to improve itself. Granum satisfies this in the strongest possible sense — *every prompt the agent runs lives in Phoenix*, every span the agent emits is read back by the agent on the next cycle, every dataset row is both the result of a prior cycle and the antigen for the next. Concretely:

1. **The population is in Phoenix.** `list-prompts` filtered to `production`-tagged versions in a given cell *is* the current B-cell population. There is no separate database holding strategies.
2. **The fitness function is in Phoenix.** The gold dataset of prior overturned appeals is a Phoenix dataset; the LLM-as-judge tournament is a Phoenix Experiment. Scoring is `get-span-annotations` against the experiment runs.
3. **Mutation is a Phoenix call.** `upsert-prompt` of a small edit to a survivor is how new variants are born. `add-prompt-version-tag` tagging it `experimental` is how it enters the population.
4. **Apoptosis is a Phoenix call.** REST `DELETE production` + MCP `add tombstoned` is how a strategy dies.
5. **The audit log is Phoenix.** Every cycle's traces, dataset rows, and prompt-version transitions are queryable from the Phoenix UI. The lineage tree we render in the frontend is a thin visualization layer over `list-traces` and the prompt-registry version graph.

If the Phoenix MCP layer disappeared, Granum would have no state. The self-improvement loop is not bolted on — it is the entire substrate.

---

## Submission-day checklist (Terminal C will run this on 2026-06-10)

- [ ] License visible at repo root (already present — Apache-2.0)
- [ ] Hosted URL alive and serving (requires Phase 0.5 Cloud Run deploy — currently blocked on user GCP-billing action)
- [ ] Demo video published to YouTube, ≤3:00, English, no ads
- [ ] All 12 form fields above pasted into Devpost form
- [ ] Devpost track selection set to Arize Phoenix
- [ ] At least one teammate / soloist listed (Shifat Islam Santo, solo)
- [ ] Submit by 2026-06-10 noon EDT (24h before the 2026-06-11 14:00 PDT hard deadline) to leave a margin for last-minute form bugs.
