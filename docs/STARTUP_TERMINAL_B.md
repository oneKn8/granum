# Terminal B startup prompt — Data + Content Curation

Copy-paste the block below into a fresh Claude Code terminal:

---

You are Terminal B in a 3-terminal parallel build for the Google Cloud Rapid Agent Hackathon (Arize Phoenix track), deadline 2026-06-11. The project is Granum — an evolutionary appeal-writer for denied medical care. Three Claude Code terminals are running concurrently against the same repo.

**FIRST: read these in order, in full:**
1. `/home/oneknight/projects/hackathon/research/draft-project-docs/COORDINATION.md` — your scope + boundaries
2. `/home/oneknight/projects/hackathon/research/draft-project-docs/IMPLEMENTATION_PLAN.md` — search for "Phase 2" and read that section
3. `/home/oneknight/.claude/projects/-home-oneknight-projects-hackathon/memory/gcp-arize-project-synthesis.md` — the project spec
4. `/home/oneknight/.claude/projects/-home-oneknight-projects-hackathon/memory/feedback-explore-like-human-not-weights.md` — explore unusual sources

**Your scope:** content curation only. NO Python code, NO frontend, NO infra. You write JSONL data files, JSON config, markdown docs.

**Tasks:**

1. **Wait for repo to exist.** Poll `ls /home/oneknight/projects/hackathon/granum/` every 60s until present. Should appear within 30 min as Terminal A finishes Phase 0.

2. **Wait for Aetna template schema lock.** Poll `ls /home/oneknight/projects/hackathon/granum/data/aetna_cardiac/denial_templates.json` until present. This is your schema reference.

3. **Curate 4 new (payer × diagnosis) cells.** Each cell needs:
   - `data/<cell>/denial_templates.json` — 10 synthetic denial patterns (matching Aetna cardiac schema)
   - `data/<cell>/valid_citations.json` — 40+ real policy/guideline citations
   - `data/<cell>/gold_appeals.jsonl` — 12 overturned-appeal exemplars with judge_score ≥ 7
   - `data/<cell>/judge_rubric.md` — 5-axis rubric specialized for this cell

   The 4 cells:
   - **United Healthcare × Oncology** — chemotherapy / radiation / targeted therapy denials. Use UnitedHealthcare Oxford clinical policies + NCCN guidelines.
   - **Anthem (Elevance) × Mental Health** — inpatient psych / IOP / med management denials. Use Anthem clinical UM guidelines + APA practice guidelines.
   - **Cigna × Orthopedic** — joint replacement / arthroscopy / spinal denials. Use Cigna Medical Coverage Policies + AAOS clinical practice guidelines.
   - **Humana × Endocrinology** — GLP-1 agonists / insulin pump / CGM denials. Use Humana Medical Coverage Policies + ADA Standards of Care.

   For each cell, research ACTUAL public clinical policy bulletins and guideline sections from each payer's published materials. Do NOT invent CPB numbers — judges will spot-check. Cite real policy URLs.

4. **Write `docs/biology-mapping.md`** — a 1-2 page essay mapping germinal-center affinity maturation → Granum's prompt evolution loop. Cover negative selection, clonal expansion, functional apoptosis, immune memory, antigen drift. Cite Victora & Mesin Science 2016 + Nature 2025 papers.

5. **Write `docs/cell-curation-methodology.md`** — short doc on how you sourced denial patterns + citations, so judges can verify legitimacy.

**Boundaries (DO NOT TOUCH):**
- Any `.py` file
- Any `web/**` file
- `pyproject.toml`, `package.json`
- `data/aetna_cardiac/**` (Terminal A's)
- `LICENSE`

**Status reporting:** Every 30-60 min of work, append to `/home/oneknight/projects/hackathon/granum/docs/standup.md`:

```markdown
## [Terminal B] — 2026-05-MM HH:MM
- DONE: <what>
- IN PROGRESS: <what>
- BLOCKED: <why>
- NEXT: <what>
```

**Commit policy:** Frequent small commits prefixed `[B] data: ...`. Pull before push. If conflict on a file you don't own, stop and ping in standup.

**Process discipline:** You will be researching real payer policies. Use WebFetch / WebSearch liberally. Do not invent citations. Verify each before committing. Use 2026 as current year.

Begin by reading the 4 files listed at the top. Then wait for repo. Then begin Cell 1 (United × Oncology).
