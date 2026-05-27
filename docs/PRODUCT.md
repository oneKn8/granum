# PRODUCT.md — What Granum Is

**Working name:** Granum (placeholder — see naming section at the end)
**Tagline:** An immune system for medical appeals.
**Status:** Draft, 2026-05-27, pre-build.

---

## 1. The problem

When a US patient is prescribed care their insurer doesn't want to pay for, the insurer issues a denial. The patient's physician can write an appeal letter. **83% of those appeals win.** Only **10% are ever filed.**

Why the gap?

- **12 hours per week** — average time a physician + staff spend on prior authorization (AMA 2023 survey).
- **35%** of physicians have at least one staff member working PA exclusively.
- **94%** of physicians report PA-related care delays.
- **78%** report patients abandoning treatment because the appeal process is too slow.

Writing an appeal isn't hard intellectually — it requires citing the right clinical guidelines, framing in the payer's specific medical-necessity language, and referencing prior similar overturned cases. It is, however, **expensive** when a physician does it manually. The hourly cost kills the appeal before it's written.

Every existing prior-auth automation company serves the payer — that's where the budget lives. **Nobody serves the denied side.** Patients lose. Physicians eat the cost or skip the appeal. Care is delayed or abandoned.

This is straight money on the ground.

---

## 2. The product

Granum is an agent that writes prior-authorization appeals on behalf of denied patients and their physicians.

It is **not** a generic LLM appeal-writer. The structural bite is that Granum **evolves its appeal strategy population over time**, tuned to each specific (payer × diagnosis) pair, based on real outcomes.

The mechanism is borrowed from immunology — affinity maturation in germinal centers. The same mechanism your B-cells use to evolve antibodies against a novel pathogen. Granum applies it to prompts.

### What a "B-cell" is in Granum

A B-cell is an appeal strategy. Concretely:
- A system prompt for drafting an appeal
- An evidence-retrieval template (which clinical guidelines to cite, which prior cases to reference, which medical-necessity language to use)
- A tool-use pattern (which Phoenix MCP tools to invoke, in which order)

Each (payer × diagnosis) cell maintains a small population of B-cell strategies — typically 5 to 12 at steady state.

### What an "antigen" is in Granum

The antigen is the **gold dataset** of prior overturned appeals for similar denials. New strategies must demonstrate fitness by drafting appeals that an LLM-as-judge scores as well or better than the prior winners, using structured English feedback (not scalar rewards — matching Arize's prompt-learning thesis).

### What "apoptosis" is in Granum

Strategies that lose the tournament are **permanently removed** from the Phoenix prompt registry. No revert. No archive. No "let's keep this around in case." Apoptosis enforces commitment.

This is the structural bite. Every other "self-improving agent" today keeps version history "just in case." Granum doesn't. The constraint forces every mutation to be a real bet, mirrors real biological selection, and makes the lineage tree honest — if a node is there, it earned its place.

### What "mutation" is in Granum

Winning strategies generate small mutations via the Phoenix MCP `upsert-prompt` tool. Mutations are deliberately tiny: swap one citation, change one clinical guideline reference, reframe one paragraph. Large rewrites are not allowed — affinity maturation works on **incremental refinement**, not regeneration.

New mutants are tagged `experimental`. Promotion to `production` requires beating the current champion on the golden dataset.

---

## 3. Why existing solutions don't work

| Existing thing | Why it doesn't solve the denied-side problem |
|---|---|
| **Cohere AI, Olive AI, etc.** (PA automation startups) | They sit between provider and payer; their business model serves the payer's cost-reduction goal. They don't help the denied side. |
| **Generic LLM appeal-writers** (GPT-4 prompt scripts) | One prompt, no learning. Doesn't improve against specific payers' patterns. Doesn't know which clinical guidelines worked last quarter for Aetna cardiac denials. |
| **EHR-integrated AI appeal modules** | Locked inside vendor walled gardens. Doesn't aggregate cross-physician outcomes. Doesn't evolve. |
| **Physician dictation tools** (Nuance DAX, etc.) | Save dictation time but don't reason about payer-specific appeal strategy. |
| **Human appeal-writing services** | Cost $200–$800 per appeal. Math breaks for low-dollar denials. |

The unfilled space is: **a learning system that improves at writing appeals for each specific payer + diagnosis combination over time, using real outcomes as the training signal, priced to be economic on every denial.**

---

## 4. Who this is for

### Direct users (v0)
- **Independent and small-group physicians** writing appeals for their own patients. They feel the 12-hours/week pain personally.
- **Patient advocates** — non-physician staff who write appeals on behalf of denied patients (legal aid clinics, hospital social workers, dedicated patient-advocacy non-profits).

### Secondary users (v0.2+)
- **Direct-to-patient** — denied patients themselves, writing their own appeals with Granum as the drafting agent.
- **Mid-size physician practices** — practices large enough to dedicate staff to PA but without enterprise EHR contracts.

### Not for (v0)
- Large hospital systems with enterprise EHR + PA modules. They have integrated solutions, however imperfect.
- Payers themselves. We're not interested in working that side of the table.

---

## 5. Why this is novel — the structural bite

Six other entries in the same hackathon track ([mender-agent](https://github.com/mattspaulding/mender-agent), [agent-sre](https://github.com/OJ-IRO/agent-sre), [tracepilot](https://github.com/bullyopswork/tracepilot), [flightcheck](https://github.com/divergent99/flightcheck), [axon](https://github.com/colinh09/axon), [Aegis-1](https://github.com/Arham-Begani/Aegis-1)) implement the **same supervisor architecture**: a meta-agent watches a target agent and patches it.

That pattern is excellent. It's also saturated. We chose a different shape:

| Axis | Supervisor pattern | Granum |
|---|---|---|
| Number of agents | 2 (target + meta) | 1 |
| Update model | Patch on diagnosis | Mutate, compete, prune |
| Version control | All versions retained | Apoptosis — losers permanently deleted |
| Selection signal | Eval score threshold | Tournament fitness vs. antigen |
| Mutation granularity | Large rewrites | Small, structured mutations only |
| Layer | Horizontal infrastructure | Vertical product (medical appeals) |
| Demo | "Watch the meta-agent patch the target" | "Watch the lineage tree grow and prune" |

The most-cited paper in the field ([Berkeley/CMU MAST](https://arxiv.org/abs/2503.13657)) documents 41–87% production failure rates across 7 multi-agent frameworks, with "every failure returning HTTP 200." The supervisor pattern's response is to add another agent above the failing agent. Granum's response is to put commitment costs on every variant — if your strategy lost, it's gone.

This is **selection pressure as the safety mechanism**, not surveillance.

---

## 6. The vision (post-hackathon)

The hackathon submission is a single (payer × diagnosis) demo cell with synthetic denials. The product trajectory is:

- **v0.1 (hackathon submission, 2026-06-11):** Single-cell demo, synthetic CMS-derived data, Aetna+cardiac as the example pair, Phoenix-rendered lineage tree, 41% → 79% measured overturn rate over 8 generations.
- **v0.2 (post-hackathon, 4–6 weeks):** Onboard 2–3 friendly independent physicians' practices, run on real denials with explicit consent + de-identified eval data, ship a patient-advocate dashboard.
- **v0.3 (3 months):** Scale to ~20 (payer × diagnosis) cells. Outcomes-as-a-service API for physician billing companies.
- **v1.0 (6 months):** Multi-payer cross-pollination — a strategy that learns to win against Aetna cardiac sometimes generalizes to United cardiac, and Granum captures that transfer learning automatically via cell embedding similarity.
- **v2.0 (12 months):** Federated cells across practices — physicians' Granum instances share anonymized fitness signals without sharing patient data. The population becomes adaptive at population-scale.

The eventual product is not "an AI that writes appeals." It is **a learning organism that gets better at fighting denials for every (payer × diagnosis) pair, indefinitely, with permanent deletion of losing strategies enforcing real commitment.**

---

## 7. What we explicitly are not doing

- **No multi-agent supervisor.** Single agent only. The germinal center is one structure, not many.
- **No version revert.** If apoptosis happens, the strategy is gone. This is the structural commitment.
- **No payer-side products.** We are the denied side, forever.
- **No EHR integration in v0.** Demo is API-driven with synthetic data.
- **No PHI in the demo.** All data is synthetic / de-identified / public-record-derived.
- **No "general-purpose appeal writer."** Granum is specifically (payer × diagnosis) scoped. Generality is the failure mode for this product.

---

## 8. The Arize fit

Phoenix MCP exposes exactly the primitives this product needs, in the rough order Granum invokes them per cycle:

| Phoenix MCP tool | Granum's use |
|---|---|
| `list-prompts` | Read current B-cell population for the matching cell |
| `get-spans`, `get-span-annotations` | Online introspection of past appeal traces and their judge annotations |
| `list-traces`, `get-trace` | Lineage reconstruction for the demo viz |
| Experiments API | Tournament scoring (candidate appeals vs. gold dataset) |
| `upsert-prompt` | Apply mutation operators to surviving strategies |
| `add-prompt-version-tag` | `experimental` → `production` promotion gate |
| `add-dataset-examples` | Write each new outcome (overturn / uphold / partial) back as antigen data |
| (registry delete) | Apoptosis — permanent removal of losing strategies |

This is the under-publicized data flywheel Arize's CPO has publicly said they want to see built. No other entry in the track has wired the full chain end-to-end.

---

## 9. On the name

"Granum" is the working name. It's Latin for *grain* / *kernel*, used in biology to refer to dense regions inside structures (chloroplast grana, germinal-center granular cells). It's deliberately weird — most projects in this hackathon are named with the same cluster of safety/governance words ("sentinel," "guardian," "mender," "axon," "shipsafe"). We want to be the one project that doesn't sound like a Claude-default.

Alternatives if Granum doesn't fit:
- **Centra** (germinal center, Latin centrum)
- **Affinity** (the immunology mechanic in plain word)
- **Overturn** (vertical-first naming — the outcome the user wants)
- **Hypermut** (the mutation operator, abbreviated)

Naming is a non-blocking concern. The product is the product.
