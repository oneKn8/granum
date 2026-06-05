# Red Queen Co-Evolution — Live + Demoed (E1) Implementation Plan


**Goal:** Make the already-built `CoEvolutionDriver` run live across many rounds, emit a real `{cell}_coevolution.json` matching the frontend `CoEvolutionState`, and light up the existing `CoEvolutionDualTree` with real writer-vs-payer lineages and apoptosis on both populations.

**Architecture:** Mirror the shipped single-population path (`GenerationalEvolution` → `to_payload()` → `runs/cell_payloads/{cell}.json` → FastAPI static serve → Next.js). Add a `CoEvolutionRun` harness that chains `CoEvolutionDriver.round()` N times, accumulates writer + payer lineage nodes, sweeps Phoenix once for final bodies/status, and serializes to `CoEvolutionState`. No live Phoenix/MCP at request time — the API stays a thin static server over the artifact.

**Tech Stack:** Python 3.12, `uv`, `typer` CLI, `pytest`/`pytest-asyncio`, `ruff`, `mypy`; Google ADK + Vertex Gemini 3.1 Pro; Arize Phoenix MCP (prompt registry + datasets); Next.js 15 frontend (already built).

**Scope:** E1 only (Red Queen live). E2 (memory+drift), E3 (transfer), E4 (honesty hardening) are separate plans authored after E1 ships. This plan produces a complete, demoable, shippable slice on its own.

**Hard rules (this repo):** run pytest as `env -u PYTHONPATH uv run pytest -q`; `source ~/.nvm/nvm.sh && nvm use default` before any `npx`; never override `git user.email` (local config is `shifatislamsanto764@gmail.com`); `git status` + `git diff --cached --stat` before every commit; work on branch `phase-d-immune-system-activation` (already created).

**Key existing interfaces (do not redefine — import and use):**
- `granum.center.coevolution.CoEvolutionDriver(phoenix, payer_agent, judge, cell, gold_path, mutation_proposer, mutation_count=2, mutation_rate_cap=0.15, adversary_reset_every=5)`; `.round()` → `CoEvolutionRoundResult`.
- `CoEvolutionRoundResult(cell, round_index, writer_winner_id, payer_winner_id, writer_loser_ids, payer_loser_ids, writer_mutant_ids, payer_mutant_ids, defensibility_composite, english_feedback, adversary_reset_fired)`.
- `granum.center.triangular_tournament.TriangularTournamentResult.all_pair_scores: tuple[PairScore(writer_id, payer_id, score)]`; `PairScore.score` is `DefensibilityScore` with `.defensibility` (0-10) and `.composite` (0-10 mean of the four sub-scores).
- `granum.adversary.payer_agent.PayerAgent(client, model, payer, diagnosis)`; `.deny(appeal, persona_id) -> Denial`.
- `granum.adversary.payer_persona.SEEDED_PERSONAS: tuple[PayerPersona(persona_id, name, system_prompt), ...]` (ids: strict, lenient, formalist, cost_focused, evidence_focused).
- `granum.center.defensibility_judge.DefensibilityJudge(client, model, rubric_path)`.
- `granum.data.seeds.seed_cell(phoenix, *, cell)`, `reset_cell(phoenix, *, cell)` (reset already wipes `{cell}_payer/*` because those names start with the cell prefix).
- `granum.center.mutation_strategies.propose_mutations(*, parent, n, seed=None)`.
- `granum.tools.gemini_client.GeminiClient().generate(model, prompt, temperature)`.
- `granum.tools.phoenix_session.phoenix_client_from_env()` (async context manager).
- Payer Phoenix name convention: `{cell}_payer/baseline_{persona_id}` and `{cell}_payer/mut_{persona_id}_{i}` (parsed by `coevolution._extract_persona_id`).
- Frontend contract `web/lib/types.ts`: `CoEvolutionState = { cell, writers: BCellStrategy[], payers: BCellStrategy[] }`; `BCellStrategy` fields = id, cell, generation, parentId, label, promptBody, mutationNote, fitness (0-1), tag (experimental|production), status (alive|tombstoned|champion), createdAt, killedAt, citations. The cell page already calls `getCoEvolution(cell)`.
- API: `GET /api/cells/{cell}/coevolution` already reads `{GRANUM_DATA_DIR}/{cell}_coevolution.json` and returns `{cell, writers:[], payers:[]}` when absent. `list_cells` already skips `*_coevolution.json`.

---

### Task 1: Carry per-population fitness in `CoEvolutionRoundResult`

The dual-tree needs a fitness per node. `round()` already computes the winner's mean composite; generalize it to a full per-id scoreboard for both populations so the runner can assign real fitness to every node (winners and losers).

**Files:**
- Modify: `src/granum/center/coevolution.py` (add two fields to `CoEvolutionRoundResult`; populate from `result.all_pair_scores`)
- Test: `tests/test_coevolution_driver.py`

- [ ] **Step 1: Write the failing test.** Add `test_round_result_exposes_per_population_scoreboards`. Reuse the existing `_make_driver` helper. Two writers (w1 wins, w2 loses) × two payers, with `score_side_effect` producing distinct defensibilities. Assert `outcome.writer_scoreboard` is a tuple of `(writer_id, mean_defensibility)` covering both writers, ordered best-first, and that w1's value equals the mean of its two pair defensibilities; assert `outcome.payer_scoreboard` likewise covers both payers using mean *inverse* defensibility (10 − d). Use `pytest.approx`.
- [ ] **Step 2: Run test to verify it fails.** Run: `env -u PYTHONPATH uv run pytest tests/test_coevolution_driver.py::test_round_result_exposes_per_population_scoreboards -v`. Expected: FAIL (`AttributeError: ... has no attribute 'writer_scoreboard'`).
- [ ] **Step 3: Implement.** Add `writer_scoreboard: tuple[tuple[str, float], ...] = ()` and `payer_scoreboard: tuple[tuple[str, float], ...] = ()` to `CoEvolutionRoundResult` (defaults keep existing tests valid). In `round()`, after the tournament, compute per-writer mean defensibility and per-payer mean inverse-defensibility from `result.all_pair_scores` (reuse the same aggregation the tournament's ranking uses), sort best-first with `prompt_id` tie-break, and pass both into the result.
- [ ] **Step 4: Run the full driver test file.** Run: `env -u PYTHONPATH uv run pytest tests/test_coevolution_driver.py -q`. Expected: PASS (new test + all 7 existing).
- [ ] **Step 5: Commit.** `git add src/granum/center/coevolution.py tests/test_coevolution_driver.py && git commit -m "feat(coevolution): expose per-population scoreboards on round result"`

---

### Task 2: `seed_payers` — seed the adversary population

**Files:**
- Modify: `src/granum/data/seeds.py` (add `seed_payers`)
- Test: `tests/test_seeds.py`

- [ ] **Step 1: Write the failing test.** Add `test_seed_payers_seeds_one_prompt_per_persona` and `test_seed_payers_is_noop_when_already_seeded`. Use an `AsyncMock` phoenix like the existing seed tests: `list_active_prompts` returns `[]` first (empty payer pop), `upsert_prompt` echoes a `PromptVersion`. Assert `seed_payers(phoenix, cell="aetna_cardiac")` upserts exactly `len(SEEDED_PERSONAS)` prompts, each name == `aetna_cardiac_payer/baseline_{persona_id}`, each tagged `("production",)`, body == that persona's `system_prompt`; and returns the upserted ids. Second test: when `list_active_prompts` returns a non-empty list, `seed_payers` upserts nothing and returns `[]`.
- [ ] **Step 2: Run to verify fail.** Run: `env -u PYTHONPATH uv run pytest tests/test_seeds.py -k seed_payers -v`. Expected: FAIL (`ImportError`/`AttributeError: seed_payers`).
- [ ] **Step 3: Implement `seed_payers(phoenix, *, cell)`** in `seeds.py`, mirroring `seed_cell`: check `list_active_prompts(name_prefix=f"{cell}_payer/")`; if non-empty return `[]`; else upsert one prompt per persona in `SEEDED_PERSONAS` at `f"{cell}_payer/baseline_{p.persona_id}"` with body `p.system_prompt`, tags `("production",)`; collect and return prompt ids. Import `SEEDED_PERSONAS` from `granum.adversary.payer_persona`.
- [ ] **Step 4: Run to verify pass.** Run: `env -u PYTHONPATH uv run pytest tests/test_seeds.py -q`. Expected: PASS.
- [ ] **Step 5: Commit.** `git add src/granum/data/seeds.py tests/test_seeds.py && git commit -m "feat(seeds): seed_payers for the adversary population"`

---

### Task 3: `CoEvolutionRun` harness + `to_payload()` → `CoEvolutionState`

**Files:**
- Create: `src/granum/center/coevolution_run.py`
- Test: `tests/test_coevolution_run.py`

Design (mirror `granum.center.evolution`): `CoEvolutionRun(driver, phoenix, cell, rounds)` with `async run() -> CoEvolutionRunResult`. Maintain two node dicts (writers, payers) keyed by prompt_id. Per round: record the `CoEvolutionRoundResult`; for each id in `writer_scoreboard`/`payer_scoreboard` create a node on first sight (generation = round index, parent_id None) else update its fitness; register spawned `writer_mutant_ids`/`payer_mutant_ids` as children of that round's respective winner (generation = round+1). After all rounds, sweep Phoenix per node for final body + status via the same `get-prompt-version-by-tag` production/tombstoned probe used in `evolution._sweep_bodies_and_status`. `to_payload()` returns `{cell, writers:[...], payers:[...]}` where each entry is a `BCellStrategy` dict: fitness normalized `round(f/10, 4)`; among non-tombstoned writers the max-fitness one is `champion`, rest `alive`; same for payers independently; tombstoned → `status="tombstoned", tag="experimental", killedAt` set; citations via the same regex helper as the single-pop payload (reuse `granum.center.evolution._citations`).

- [ ] **Step 1: Write the failing test.** Add `tests/test_coevolution_run.py::test_run_accumulates_both_lineages_and_serializes_payload`. Build a fake driver whose `round()` is an `AsyncMock` with `side_effect` returning 2 hand-built `CoEvolutionRoundResult`s (round 0: writers w1(win)/w2(lose), payers p1(win)/p2(lose), scoreboards populated, 1 writer mutant `wm1` + 1 payer mutant `pm1`; round 1: w1 vs wm1, p1 vs pm1, w2/p2 already tombstoned). Mock `phoenix._mcp.call_tool` so the production probe resolves bodies for survivors and the tombstoned probe resolves for w2/p2 (mirror the stubbing style in `tests/test_evolution.py`). Run `CoEvolutionRun(driver, phoenix, "aetna_cardiac", rounds=2)`, then `to_payload()`. Assert: payload has keys `cell, writers, payers`; writers include w1 (status `champion`), w2 (`tombstoned`, killedAt set), wm1 (generation 1, parentId w1); payers include p1 (`champion`), p2 (`tombstoned`), pm1 (gen 1, parentId p1); all `fitness` in [0,1]; shape matches `CoEvolutionState` field names (camelCase keys: parentId, promptBody, mutationNote, killedAt).
- [ ] **Step 2: Run to verify fail.** Run: `env -u PYTHONPATH uv run pytest tests/test_coevolution_run.py -v`. Expected: FAIL (module/class not found).
- [ ] **Step 3: Implement** `coevolution_run.py` per the design above (dataclasses `CoEvNode` accumulator + `CoEvolutionRunResult` with `to_payload()`). Reuse `_citations` and the sweep-probe approach from `granum.center.evolution`.
- [ ] **Step 4: Run to verify pass.** Run: `env -u PYTHONPATH uv run pytest tests/test_coevolution_run.py -q`. Expected: PASS.
- [ ] **Step 5: Commit.** `git add src/granum/center/coevolution_run.py tests/test_coevolution_run.py && git commit -m "feat(coevolution): CoEvolutionRun harness + CoEvolutionState payload"`

---

### Task 4: `granum coevolve` CLI command

**Files:**
- Modify: `src/granum/cli.py` (add `coevolve` command, mirroring `evolve`)
- Test: `tests/test_smoke.py` (add a CLI-surface assertion; the live path is exercised in Task 6, not unit tests)

The command signature: `coevolve(cell="aetna_cardiac", rounds=8, mutation_count=2, reset=False)`. Env gate identical to `evolve` (require `GOOGLE_CLOUD_PROJECT`, `PHOENIX_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT`). Body (async, mirror `evolve`): register Phoenix OTel tracer; build `GeminiClient`, `DefensibilityJudge(client, model, rubric_path=Path("data/judge_rubric.md"))`, `PayerAgent(client, model, payer, diagnosis)`; open `phoenix_client_from_env()`; if `reset` call `reset_cell`; call `seed_cell` then `seed_payers`; build `CoEvolutionDriver(phoenix, payer_agent, judge, cell, gold_path=f"data/{cell}/gold_appeals.jsonl", mutation_proposer=propose_mutations, mutation_count=...)`; run `CoEvolutionRun(driver, phoenix, cell, rounds).run()`; write `runs/cell_payloads/{cell}_coevolution.json` (the payload from `to_payload()`); echo a per-round summary (round, defensibility composite, writer/payer apoptosis counts) and the artifact path.

- [ ] **Step 1: Write the failing test.** In `tests/test_smoke.py` add `test_coevolve_command_registered_and_env_gated`: use Typer's `CliRunner` to invoke `coevolve` with the three required env vars unset (monkeypatch `os.environ`); assert exit code != 0 and the stderr names the missing env vars (mirror any existing `cycle`/`evolve` smoke test). This verifies the command exists and is wired without making live calls.
- [ ] **Step 2: Run to verify fail.** Run: `env -u PYTHONPATH uv run pytest tests/test_smoke.py -k coevolve -v`. Expected: FAIL (no such command).
- [ ] **Step 3: Implement** the `coevolve` command in `cli.py` as specified above.
- [ ] **Step 4: Run to verify pass + lint/type.** Run: `env -u PYTHONPATH uv run pytest tests/test_smoke.py -k coevolve -q && env -u PYTHONPATH uv run ruff check src/granum/cli.py && env -u PYTHONPATH uv run mypy src/granum/cli.py`. Expected: PASS / clean.
- [ ] **Step 5: Commit.** `git add src/granum/cli.py tests/test_smoke.py && git commit -m "feat(cli): granum coevolve — live Red Queen co-evolution run"`

---

### Task 5: API serves the co-evolution artifact (smoke test)

**Files:**
- Test: `tests/test_api.py` (add a coevolution-served case; endpoint code already exists)

- [ ] **Step 1: Write the failing test.** Add `test_coevolution_endpoint_serves_artifact_when_present`. Mirror the existing `test_api.py` fixture that points `GRANUM_DATA_DIR` at a tmp dir. Write a minimal `aetna_cardiac_coevolution.json` (`{"cell":"aetna_cardiac","writers":[...one BCellStrategy...],"payers":[...one...]}`) into the tmp dir; GET `/api/cells/aetna_cardiac/coevolution` via FastAPI `TestClient`; assert 200, `cell=="aetna_cardiac"`, and writers/payers non-empty. Also assert `/api/cells` does NOT list the coevolution file as a cell.
- [ ] **Step 2: Run to verify fail or pass.** Run: `env -u PYTHONPATH uv run pytest tests/test_api.py -k coevolution -v`. Expected: PASS if the artifact-serving path is already correct (endpoint exists); if it FAILS, fix the endpoint/`list_cells` filter until green. (This task is a guard, not new feature code.)
- [ ] **Step 3: Run full API test file.** Run: `env -u PYTHONPATH uv run pytest tests/test_api.py -q`. Expected: PASS.
- [ ] **Step 4: Commit.** `git add tests/test_api.py src/granum/web/api.py && git commit -m "test(api): coevolution endpoint serves artifact; cells list excludes it"`

---

### Task 6: First live co-evolution run + curate the demo artifact

Live, supervised (real Gemini + Phoenix cost — user approved max quality). Run several; keep the cleanest honest arc.

**Files:** writes `runs/cell_payloads/aetna_cardiac_coevolution.json`; curated copy → `api_data/aetna_cardiac_coevolution.json`.

- [ ] **Step 1: Load env.** Run: `set -a; source .env; set +a` then confirm `env -u PYTHONPATH uv run granum doctor` prints "All required env vars present."
- [ ] **Step 2: Run the live Red Queen.** Run: `env -u PYTHONPATH uv run granum coevolve --cell aetna_cardiac --rounds 8 --reset --mutation-count 2`. Expected: per-round summary lines + "artifact: runs/cell_payloads/aetna_cardiac_coevolution.json". If a live MCP/Gemini call breaks: STOP, reproduce, root-cause against the real response (capture-then-code), fix, re-run — do not assume schemas.
- [ ] **Step 3: Inspect the artifact (evidence, not vibes).** Confirm the JSON has both `writers` and `payers` with real bodies, ≥1 tombstoned node in EACH population (apoptosis on both sides), generations spanning the rounds, and fitness values in [0,1]. Re-run step 2 a few times (vary `--rounds`/seed) and keep the run with the clearest dual-population climb + visible extinctions on both sides.
- [ ] **Step 4: Bake the curated artifact.** Copy the chosen `runs/cell_payloads/aetna_cardiac_coevolution.json` to `api_data/aetna_cardiac_coevolution.json`.
- [ ] **Step 5: Commit.** `git add api_data/aetna_cardiac_coevolution.json && git commit -m "data(coevolution): curated live Red Queen artifact for aetna_cardiac"` (runs/ is gitignored; do not add it).

---

### Task 7: Local end-to-end verification (real data in the browser)

**Files:** none (verification only).

- [ ] **Step 1: Start the API over the curated data.** Run (sandbox-disabled, real host): `GRANUM_DATA_DIR=api_data env -u PYTHONPATH uv run uvicorn granum.web.api:app --host 0.0.0.0 --port 8090`. Confirm `curl -s localhost:8090/api/cells/aetna_cardiac/coevolution` returns non-empty writers + payers.
- [ ] **Step 2: Start the frontend against it.** Run: `source ~/.nvm/nvm.sh && nvm use default && cd web && NEXT_PUBLIC_USE_REAL_API=true NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8090 PORT=3000 npx next dev`.
- [ ] **Step 3: Playwright-verify the dual tree renders real data.** Navigate to `http://127.0.0.1:3000/cell/aetna_cardiac`, take a full-page screenshot, and confirm `CoEvolutionDualTree` shows two populations with survivors branching and extinct nodes greyed on both sides. Save the screenshot for the demo.
- [ ] **Step 4: Record the result** in `docs/standup.md` (one line: live Red Queen E2E-verified, both-population apoptosis visible, artifact baked).
- [ ] **Step 5: Commit.** `git add docs/standup.md && git commit -m "docs(standup): Red Queen co-evolution live + E2E-verified"`

---

### Task 8: Full-suite gate + open PR

**Files:** none (gate + PR).

- [ ] **Step 1: Full test suite.** Run: `env -u PYTHONPATH uv run pytest -q`. Expected: all pass (182 prior + the new co-evolution-run, seeds, smoke, api tests).
- [ ] **Step 2: Lint + types.** Run: `env -u PYTHONPATH uv run ruff check . && env -u PYTHONPATH uv run mypy src/granum`. Expected: clean.
- [ ] **Step 3: Scope check + push.** Run: `git status && git diff --cached --stat` (must be empty — all work committed); then `git push -u origin phase-d-immune-system-activation`.
- [ ] **Step 4: Open PR.** Run: `gh pr create --title "E1: Red Queen co-evolution live + demoed" --body "Activates the built-but-dormant dual-population co-evolution: per-population scoreboards, seed_payers, CoEvolutionRun harness + CoEvolutionState payload, granum coevolve CLI, curated live artifact, E2E-verified dual-tree. Closes E1 of the immune-system-activation spec."`

---

## Self-review

- **Spec coverage (E1 slice):** acceptance criterion 1 (Red Queen live, real artifact, dual-tree with both-side apoptosis) is covered by Tasks 1–7; criterion 5 quality gates by Tasks 4/8. E2/E3/E4 are explicitly out of this plan (separate plans).
- **Placeholder scan:** no TBD/TODO; each task names exact files, exact commands, and concrete assertions. Tests are described by name + assertions rather than full code per this repo's "no code in planning docs" rule — the engineer writes the bodies during execution.
- **Type consistency:** field names match `web/lib/types.ts` (`parentId`, `promptBody`, `mutationNote`, `killedAt`, `fitness` 0-1, `status` alive|tombstoned|champion). New `CoEvolutionRoundResult` fields (`writer_scoreboard`, `payer_scoreboard`) are referenced consistently in Tasks 1 and 3. Reused symbols (`_citations`, sweep probe) point at real `granum.center.evolution` members.
- **Risk note:** Task 6 is the only nondeterministic step (live Red Queen noise/cost) — mitigated by curate-best-of-several and the bug protocol.
</content>
