# Granum: Devpost Submission Text

> Source-of-truth for every Devpost form field. Copy-paste directly into the form on submission day. Last revised 2026-06-09; deadline 2026-06-11 14:00 PDT.

---

## 1. Project name

**Granum**

## 2. Elevator pitch (≤ 200 chars)

> An immune system for medical appeals. Granum evolves a population of appeal strategies per payer and diagnosis; winners mutate, losers are apoptosed. Built on Arize Phoenix MCP and Gemini 3.1 Pro.

(196 characters incl. spaces.)

## 3. Inspiration

US insurers deny medically necessary care to millions of patients every year. The AMA's *Prior Authorization Physician Survey* documents the resulting pain in specific numbers: physicians spend an average of **12 hours per week** on prior-authorization work, **94%** report PA-related care delays, and **78%** see patients abandon treatment because the appeal process is too slow. The cruel twist: **83% of appeals that are actually filed succeed**, but **only ~10% of denials are ever appealed at all**, because writing one costs twelve hours of a physician's time at three hundred dollars an hour. The math kills the appeal before it's ever written.

Every prior-auth automation startup I surveyed serves the payer, because that's where the budget lives. Nobody serves the denied side. I wanted to fix the side where patients lose.

Separately, I was reading about affinity maturation in germinal centers (Victora & Mesin, *Science* 2016): the immune-system mechanism by which B-cells evolve antibodies against a novel pathogen via somatic hypermutation, antigen-driven tournament selection, and apoptosis of low-affinity variants. The structural property that makes germinal centers honest is commitment. A B-cell that loses the tournament does not survive. There is no archive, no revert. That constraint forces every mutation to be a real bet.

Evolving prompts is not new on its own. PromptBreeder and EvoPrompt already treat a population of prompts as a genetic population and refine it with mutation and selection. But every such system keeps full version history, just in case, and reverts when a variant underperforms. That safety net quietly removes the commitment that makes germinal centers honest. I could not find anyone who had built prompt evolution with *permanent apoptosis* (losers retired for good, no revert), run it on a *prompt registry as the literal genome* (versions are lineage, tags are life and death), and pointed it at a real vertical where the stakes are a denied patient. That synthesis is Granum.

Granum is the answer.

## 4. What it does

Granum is a single ADK agent that drafts prior-authorization appeals on behalf of denied patients and their physicians. Unlike a generic LLM appeal-writer, it maintains a small evolving population of appeal **strategies** for each (payer × diagnosis) cell. A strategy is a system prompt, an evidence-retrieval template, and a tool-use pattern.

Each generation in a cell runs the germinal cycle:

1. **Selection.** Granum picks the top-K surviving strategies as candidates.
2. **Negative selection.** A thymic-style guard pre-kills any draft with a hallucinated citation, an unsupported clinical claim, or a missing deadline reference. Hallucination defense happens *before* the tournament, not after.
3. **Tournament.** Every surviving candidate drafts an appeal; an LLM-as-judge scores each one against a gold dataset of prior overturned appeals using a 5-axis rubric with median-of-3 sampling, producing **structured English feedback** (no scalar rewards, matching Arize's prompt-learning thesis).
4. **Submission.** The winning candidate's appeal is dispatched (mocked endpoint in this build).
5. **Outcome ingestion.** The result is written back to a Phoenix dataset via `add-dataset-examples`. The dataset *is* the antigen.
6. **Apoptosis (Path B).** Losing strategies have their `production` tag removed via Phoenix REST and a `tombstoned` tag added via MCP. Phoenix prompt versions are immutable by design, so this is functional apoptosis: the strategy is structurally ineligible for future selection or mutation, the full audit lineage is preserved, and there is no revert.
7. **Mutation.** Surviving strategies generate small mutations via Phoenix MCP `upsert-prompt`. Mutations are deliberately tiny: swap one citation, change one clinical guideline reference, reframe one paragraph. Large rewrites are banned, because affinity maturation is incremental.

Two further mechanisms are built and unit-tested for multi-cell operation: **immune memory** (old champions are tagged `memory_cell` and reactivated after two consecutive extinctions) and **antigen drift** (when denial patterns shift past a threshold, dormant memory cells are retested against the new distribution).

Four cells are curated with real data: Aetna+cardiac, United+oncology, Anthem+mental-health, Humana+endocrinology. Each has 22+ denial patterns, 40+ verified clinical-policy citations, 12 gold overturned-appeal exemplars, and a 5-axis judge rubric. Two of them have evolved end-to-end on live Phoenix + Vertex Gemini:

- **Aetna+cardiac:** judge-rated overturn likelihood **0.40 → 0.98** over 10 generations, 18 strategies apoptosed.
- **United+oncology:** **0.62 → 0.98** over 10 generations, 18 strategies apoptosed.

Granum also tests **cross-cell strategy transfer**. Promoting `united_oncology`'s champion into `aetna_cardiac` produced a significant lift (+1.92 composite on the 0–10 judge scale, p = 0.024, 5/5 trials pass negative selection), so it was promoted. The reverse, `aetna_cardiac` → `united_oncology`, was rejected: the Aetna champion is too citation-rigid to generalize, and all 5 trials failed negative selection. The asymmetry is the honest result, not a bug.

The product is the lineage tree, a phylogenetic visualization of every strategy that ever existed in a cell. Survivors branch. Apoptosed nodes grey out with strikethrough lineage. The fitness curve climbs generation over generation.

## 5. How we built it

**Stack.**

- **Agent runtime:** [Google ADK](https://google.github.io/adk-docs/) (Python 3.12, uv-managed)
- **Reasoning model:** Gemini 3.1 Pro (`gemini-3.1-pro-preview`) on Vertex AI; `gemini-3.5-flash` for high-volume mutation calls
- **Observability + evolution backbone:** [Arize Phoenix](https://arize.com/docs/phoenix) Cloud + [`@arizeai/phoenix-mcp`](https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp) + Phoenix REST for tag mutation
- **API:** FastAPI on Google Cloud Run (us-central1)
- **State:** Phoenix prompt registry + datasets (the population literally lives in Phoenix)
- **Frontend:** Next.js 15 (App Router) + React 19 + Tailwind on Vercel, D3 for the phylogenetic lineage tree, Recharts for fitness curves
- **License:** Apache-2.0

**Phoenix MCP tool chain (end-to-end, no decorative wrapping).**

| Tool | Where Granum uses it |
|---|---|
| `list-prompts` | Read current B-cell population for the matching cell |
| `upsert-prompt` | Apply mutation operators to surviving strategies |
| `add-prompt-version-tag` | `experimental` → `production` promotion; also `memory_cell`, `tombstoned` |
| REST `DELETE /prompts/.../tags/production` | Path B apoptosis, strip champion status |
| `add-dataset-examples` | Write each new appeal outcome back as antigen data |
| `get-spans`, `get-span-annotations` | Online introspection of past appeal traces and judge annotations |
| `list-traces`, `get-trace` | Lineage reconstruction for the visualization |
| Experiments API | Tournament scoring (candidate appeals vs. gold dataset) |

All Phoenix interaction is mediated by a single seam under `src/granum/tools/`. No other Granum module references Phoenix tool names or REST paths, which kept the immutability pivot (below) contained to one file.

**Process discipline.** I worked from a numbered, phased plan with named failure modes per phase, and kept CI green from day one. Every backend module was built test-first, which is why the germinal cycle, the Red Queen co-evolution, and the cross-cell transfer harness each have integration tests, not just unit tests. The frontend went through an explicit polish pass for accessibility, motion performance, and metadata before recording.

## 6. Challenges we ran into

**Phoenix prompt versions are immutable.** My original design assumed `delete-prompt-version` existed. The pre-flight Phoenix MCP capability audit (27 tools enumerated against a live workspace) proved it doesn't, and shouldn't, because prompt registries are supposed to be append-only audit logs. I pivoted to **Path B**: *functional* apoptosis via tag mutation. Removing `production` from a strategy and adding `tombstoned` makes the strategy structurally ineligible for selection or mutation while preserving the full audit lineage. The biology metaphor actually gets *stronger*: in real germinal centers, apoptosed B-cells are also not literally erased; they're flagged for clearance by tingible-body macrophages. Tags as macrophages.

**LLM-as-judge circularity.** The load-bearing flaw in any judge-scored evolution loop is well known: if the judge shares priors with the generator, you climb a fake fitness gradient. My response is a **co-evolutionary Red Queen**. A second adversarial *payer-agent* population evolves in parallel, actively looking for hallucinations and policy-citation weaknesses in candidate appeals. Survival means defeating an adversary, not impressing a judge. The `granum coevolve` command ships five seeded payer personas (strict / lenient / formalist / cost-focused / evidence-focused) driven by `PayerAgent`, a triangular `writer × payer × judge` tournament with anti-degeneracy regularization (mutation cap 15%, adversary reset every 5 generations), and a `CoEvolutionDriver` that alternates writer and payer evolution per cell. Verified via a five-round integration test covering all 8 gate criteria.

**Avoiding the field's crowded pattern.** The common shape for a self-improving agent is the hierarchical *supervisor*: a meta-agent watches a target agent and patches it on diagnosis. That pattern is excellent, and it is everywhere. I took the structural inverse. A supervisor adds a babysitter; Granum puts commitment costs on every idea instead, so the system improves by killing its own weak strategies. One organism, evolutionary peer competition, permanent apoptosis, no second agent watching the first.

**The 12-hour-per-physician math is true. The 83% overturn-rate is true. The 10% file-rate is true.** Every number I cite resolves to AMA, KFF, or CMS public-record data. I caught myself once about to use a "trusted by 10K hospitals" framing, and the anti-slop checklist in `web/DESIGN.md` killed it before it shipped.

## 7. Accomplishments we're proud of

- **Two cells evolved end-to-end on live infrastructure.** Aetna+cardiac climbed 0.40 → 0.98 and United+oncology climbed 0.62 → 0.98, each over 10 generations with 18 apoptosed strategies, on real Phoenix + Vertex Gemini, not mocks.
- **Cross-cell transfer ran live and gave an honest result.** United → Aetna was promoted (+1.92 composite, p = 0.024, 5/5 trials clean). Aetna → United was rejected (champion too citation-rigid, 5/5 trials failed negative selection). The promote gate (p < 0.05 and lift ≥ 1.0 → `transferred` tag) held both ways.
- **Full Phoenix MCP chain wired end-to-end.** All eight Phoenix surfaces are load-bearing; pull any one out and the agent stops working.
- **A novel structural primitive (apoptosis-via-tag) that survived contact with reality.** The Path B pivot off the immutability constraint made the metaphor *more* honest, not less.
- **Four curated cells, real citations.** Every CPT / HCPCS / ICD-10 code in the synthetic data is real. Every payer-policy ID resolves to a real document. Every clinical-guideline citation resolves to a real URL. The gold-appeal dataset (48 exemplars across 4 cells) passes negative selection clean: zero hallucinated citations across the entire corpus.
- **Honest test coverage.** 259 tests passing; `ruff` and `mypy` clean. Every mutation operator, judge axis, tournament protocol, immune-memory primitive, antigen-drift detector, payer persona, triangular tournament, defensibility judge, co-evolution driver, cross-cell embedder, and transfer-trial harness is tested; integration tests cover the full germinal cycle, a five-round Red Queen run, and the cross-cell promotion gate.
- **The frontend is the demo.** The lineage tree (D3 hierarchy + zoom), the prompt-diff component (word-level with citation deltas), and the fitness curve (synchronized with the generation tick) render real cell payloads, with a deterministic offline fallback so the demo holds if Phoenix is down.
- **A `web/DESIGN.md` and a banned-defaults checklist.** The frontend uses IBM Plex Serif + JetBrains Mono on OKLCH-tuned cell-stain blues and apoptosis red. No Inter, no Space Grotesk, no purple-blue gradients, no centered hero with two CTAs, no "trusted by" logo strip.

## 8. What we learned

- **Affinity maturation generalizes.** The germinal-center mechanism is a remarkably good description of how *any* learning system that has access to a quality signal but no gradient should structure its search. The Arize team's "prompt learning over scalars" thesis is exactly this: English-feedback judge scores are the antigen.
- **Phoenix MCP is more capable than its docs advertise.** The combination of prompt-registry tag move-semantics + dataset-writeback + span retrieval is a self-improvement substrate hiding in plain sight. I had to read the source code of the MCP server to discover that `add-prompt-version-tag` is move-semantic, which turned out to be the atomic primitive I needed for champion-swap.
- **Permanent deletion is psychologically heavy and structurally clean.** Apoptosis enforces commitment in a way that "revert if the new prompt is worse" doesn't. Knowing the loser is *gone* changes how aggressively you mutate.
- **The hard part is restraint, not generation.** Banning large rewrites and forcing only single-knob mutations (citation swap / paragraph reframe / clinical-guideline substitution) is what makes the lineage tree readable.

## 9. What's next

- **Evolve the remaining curated cells.** Anthem+mental-health and Humana+endocrinology are fully curated (data, citations, gold appeals, rubrics) but have not yet been run live. Next is evolving all four, then running cross-cell transfer across the full matrix to map which strategies generalize, and curating new cells (Cigna+orthopedic is next on the list).
- **Live payer co-evolution at scale.** The Red Queen loop is built; the next step is running it continuously across every cell so each writer population trains against a perpetually adapting adversary, not a fixed one.
- **Real denials, with consent.** Onboard 2–3 independent physician practices, run on real denials with explicit consent and de-identified eval data, and ship a patient-advocate dashboard.
- **Federated cells across practices.** Granum instances share anonymized fitness signals without sharing patient data, so the population becomes adaptive at population scale.

The eventual product is not "an AI that writes appeals." It is **a learning organism that gets better at fighting denials for every (payer × diagnosis) pair, indefinitely, with real commitment costs on every variant enforcing real selection.**

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
- **Live app:** https://granum-oneknights-projects.vercel.app
- **Live API:** https://granum-api-lpgmo76lta-uc.a.run.app
- **Demo video:** linked on the Devpost project page
- **Devpost project page:** *(fill once the form is created)*

## 12. Track selection

**Arize Phoenix track.**

### Arize-specific scoring overlay: self-improvement loop write-up

The Arize track has a published bonus criterion: the agent uses its own observability data to improve itself. Granum satisfies this in the strongest possible sense. *Every prompt the agent runs lives in Phoenix*, every span the agent emits is read back by the agent on the next cycle, and every dataset row is both the result of a prior cycle and the antigen for the next. Concretely:

1. **The population is in Phoenix.** `list-prompts` filtered to `production`-tagged versions in a given cell *is* the current B-cell population. There is no separate database holding strategies.
2. **The fitness function is in Phoenix.** The gold dataset of prior overturned appeals is a Phoenix dataset; the LLM-as-judge tournament is a Phoenix Experiment. Scoring is `get-span-annotations` against the experiment runs.
3. **Mutation is a Phoenix call.** `upsert-prompt` of a small edit to a survivor is how new variants are born. `add-prompt-version-tag` tagging it `experimental` is how it enters the population.
4. **Apoptosis is a Phoenix call.** REST `DELETE production` + MCP `add tombstoned` is how a strategy dies.
5. **The audit log is Phoenix.** Every cycle's traces, dataset rows, and prompt-version transitions are queryable from the Phoenix UI. The lineage tree rendered in the frontend is a thin visualization layer over `list-traces` and the prompt-registry version graph.

If the Phoenix MCP layer disappeared, Granum would have no state. The self-improvement loop is not bolted on. It is the entire substrate.

---

## Submission-day checklist (run on 2026-06-10)

- [x] License visible at repo root (Apache-2.0)
- [x] Hosted URL alive and serving (Vercel frontend + Cloud Run API live)
- [ ] Demo video published, ≤3:00, English, no ads
- [ ] All 12 form fields above pasted into Devpost form
- [ ] Devpost track selection set to Arize Phoenix
- [ ] At least one teammate / soloist listed (Shifat Islam Santo, solo)
- [ ] Submit by 2026-06-10 noon EDT (24h before the 2026-06-11 14:00 PDT hard deadline) to leave a margin for last-minute form bugs.
