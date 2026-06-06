"""Granum CLI entry point."""
import typer

app = typer.Typer(help="Granum — an immune system for medical appeals.")


@app.command()
def doctor() -> None:
    """Verify env vars, Vertex access, Phoenix auth."""
    import os
    required = ["GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        typer.echo(f"MISSING: {', '.join(missing)}", err=True)
        raise typer.Exit(code=1)
    typer.echo("All required env vars present.")


@app.command()
def version() -> None:
    """Print version."""
    typer.echo("granum 0.1.0")


@app.command(name="cycle-all")
def cycle_all(
    cell: str | None = typer.Option(None, "--cell", help="Limit to one cell id"),
    rounds: int = typer.Option(1, "--rounds", help="Number of rounds to run"),
) -> None:
    """Run germinal-cycle rounds across all validated cells.

    Requires live Phoenix + Vertex Gemini auth (Phase 0.4 user actions:
    GCP billing, ADC login, Phoenix Cloud API key).
    """
    import os
    missing = [
        k for k in ("GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT")
        if not os.getenv(k)
    ]
    if missing:
        typer.echo(
            f"cycle-all requires env: {', '.join(missing)}. "
            "Complete Phase 0.4 user actions first (see docs/standup.md).",
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo("cycle-all stub — live wiring lands when Phoenix client is connected (Phase 1.10).")


@app.command()
def cycle(
    cell: str = typer.Option("aetna_cardiac", "--cell", help="Cell id, e.g. aetna_cardiac"),
    seed_value: int = typer.Option(42, "--seed-value", help="Deterministic denial seed"),
    mutation_count: int = typer.Option(2, "--mutation-count", help="Mutants spawned from winner"),
) -> None:
    """Run ONE live germinal cycle for a cell against real Phoenix + Vertex Gemini.

    The honest loop: each active B-cell drafts an appeal for a synthetic denial,
    a Vertex Gemini judge scores the appeals, the loser strategies are tombstoned
    in Phoenix (apoptosis, Path B), the winner is promoted to `production`, and
    K mutant prompt-versions are spawned. A run artifact is written to runs/.
    """
    import asyncio
    import json
    import os
    from pathlib import Path

    required = ("GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        typer.echo(
            f"cycle requires env: {', '.join(missing)}. Run `set -a; source .env; set +a` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        payer, diagnosis = cell.split("_", 1)
    except ValueError:
        typer.echo(f"--cell must look like 'payer_diagnosis' (got {cell!r})", err=True)
        raise typer.Exit(code=2)

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

    from granum.center.cycle import GerminalCycle
    from granum.center.judge import LLMJudge
    from granum.center.mutation_strategies import propose_mutations
    from granum.center.prompt_mutation import (
        citation_hint_for_cell,
        make_llm_mutator,
        resolve_mutator_model,
    )
    from granum.data.denials import Denial, generate_denial
    from granum.tools.gemini_client import GeminiClient
    from granum.tools.phoenix_session import phoenix_client_from_env

    gemini = GeminiClient()

    async def gen_appeal(system_prompt: str, denial: Denial) -> str:
        prompt = (
            f"{system_prompt}\n\n"
            f"## Denial to appeal\n{denial.denial_text}\n\n"
            f"Payer: {denial.payer} | Diagnosis: {denial.diagnosis} | "
            f"CPT {denial.cpt_code} | ICD-10 {denial.icd10_code} | "
            f"Patient age {denial.patient_age_range} | "
            f"Appeal deadline {denial.appeal_deadline_days} days.\n\n"
            "Write the complete appeal letter now. Output only the letter."
        )
        return await gemini.generate(model=model, prompt=prompt, temperature=0.3)

    async def _run() -> None:
        # Export the cycle's OTel spans to Phoenix so the run shows up as real
        # traces (Phoenix is the demo's system of record).
        try:
            from phoenix.otel import register

            endpoint = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
            api_key = os.environ["PHOENIX_API_KEY"]
            register(
                project_name=os.getenv("PHOENIX_PROJECT_NAME", "granum"),
                endpoint=f"{endpoint}/v1/traces",
                headers={"api_key": api_key, "authorization": f"Bearer {api_key}"},
                batch=False,
                set_global_tracer_provider=True,
            )
        except Exception as exc:  # noqa: BLE001 — tracing is supplementary
            typer.echo(f"WARN: Phoenix tracer registration failed: {exc}", err=True)

        _cell_rubric = Path(f"data/{cell}/judge_rubric.md")
        judge = LLMJudge(
            client=gemini,
            model=model,
            rubric_path=_cell_rubric
            if _cell_rubric.exists()
            else Path("data/judge_rubric.md"),
        )
        denial = generate_denial(payer=payer, diagnosis=diagnosis, seed=seed_value)
        typer.echo(f"Denial {denial.denial_id} ({denial.denial_reason}) — running live cycle…")

        async with phoenix_client_from_env() as phoenix:
            cyc = GerminalCycle(
                phoenix=phoenix,
                judge=judge,
                cell=cell,
                valid_citations_path=f"data/{cell}/valid_citations.json",
                gold_path=f"data/{cell}/gold_appeals.jsonl",
                mutation_proposer=propose_mutations,
                mutation_count=mutation_count,
                appeal_generator=gen_appeal,
                prompt_mutator=make_llm_mutator(
                    client=gemini,
                    model=resolve_mutator_model(model),
                    citation_hint=citation_hint_for_cell(cell),
                ),
            )
            outcome = await cyc.run(denial=denial)

        runs_dir = Path("runs")
        runs_dir.mkdir(exist_ok=True)
        artifact = runs_dir / f"{cell}_seed{seed_value}_{denial.denial_id}.json"
        artifact.write_text(
            json.dumps(
                {
                    "cell": outcome.cell,
                    "denial_id": outcome.denial_id,
                    "model": model,
                    "winner_id": outcome.winner_id,
                    "winner_version_id": outcome.winner_version_id,
                    "winner_composite_score": outcome.winner_composite_score,
                    "scoreboard": [list(s) for s in outcome.scoreboard],
                    "rejected_by_negative_selection": list(outcome.rejected_by_negative_selection),
                    "tombstoned_ids": list(outcome.tombstoned_ids),
                    "mutant_ids": list(outcome.mutant_ids),
                    "english_feedback": outcome.english_feedback,
                    "winner_appeal": outcome.winner_appeal,
                },
                indent=2,
            )
        )

        typer.echo("")
        typer.echo("=== CYCLE COMPLETE (live) ===")
        for pid, comp in sorted(outcome.scoreboard, key=lambda x: -x[1]):
            marker = "WIN " if pid == outcome.winner_id else "    "
            typer.echo(f"  {marker}{pid}: composite={comp:.2f}")
        typer.echo(f"  winner: {outcome.winner_id} (composite {outcome.winner_composite_score:.2f})")
        typer.echo(f"  tombstoned: {list(outcome.tombstoned_ids)}")
        typer.echo(f"  mutants spawned: {list(outcome.mutant_ids)}")
        typer.echo(f"  artifact: {artifact}")

    asyncio.run(_run())


@app.command()
def evolve(
    cell: str = typer.Option("aetna_cardiac", "--cell", help="Cell id, e.g. aetna_cardiac"),
    generations: int = typer.Option(8, "--generations", help="Number of generations"),
    seed_value: int = typer.Option(42, "--seed-value", help="Deterministic antigen seed"),
    mutation_count: int = typer.Option(2, "--mutation-count", help="Daughters per generation"),
    survival_count: int = typer.Option(
        1, "--survival-count",
        help="Elitist top-K survival per generation (>1 keeps diversity; 1 = winner-take-all)",
    ),
    reset: bool = typer.Option(
        False, "--reset", help="Hard-wipe + reseed the cell before evolving (clean run)"
    ),
) -> None:
    """Run a multi-generation evolution for a cell and persist a CellPayload artifact.

    The population affinity-matures against a consistent antigen (the same
    denial each generation). Writes runs/cell_payloads/{cell}.json (the camelCase
    CellPayload the frontend consumes) + a full artifact with appeals.
    """
    import asyncio
    import os
    from pathlib import Path

    required = ("GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        typer.echo(f"evolve requires env: {', '.join(missing)}. Source .env first.", err=True)
        raise typer.Exit(code=1)

    try:
        payer, diagnosis = cell.split("_", 1)
    except ValueError:
        typer.echo(f"--cell must look like 'payer_diagnosis' (got {cell!r})", err=True)
        raise typer.Exit(code=2)

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

    from granum.center.cycle import GerminalCycle
    from granum.center.evolution import GenerationalEvolution
    from granum.web.payload_io import write_payload_atomic
    from granum.center.judge import LLMJudge
    from granum.center.mutation_strategies import propose_mutations
    from granum.center.prompt_mutation import (
        citation_hint_for_cell,
        make_llm_mutator,
        resolve_mutator_model,
    )
    from granum.data.denials import Denial, generate_denial
    from granum.data.seeds import reset_cell, seed_cell
    from granum.tools.gemini_client import GeminiClient
    from granum.tools.phoenix_session import phoenix_client_from_env

    gemini = GeminiClient()

    async def gen_appeal(system_prompt: str, denial: Denial) -> str:
        prompt = (
            f"{system_prompt}\n\n## Denial to appeal\n{denial.denial_text}\n\n"
            f"Payer: {denial.payer} | Diagnosis: {denial.diagnosis} | "
            f"CPT {denial.cpt_code} | ICD-10 {denial.icd10_code} | "
            f"Patient age {denial.patient_age_range} | "
            f"Appeal deadline {denial.appeal_deadline_days} days.\n\n"
            "Write the complete appeal letter now. Output only the letter."
        )
        return await gemini.generate(model=model, prompt=prompt, temperature=0.3)

    async def _run() -> None:
        try:
            from phoenix.otel import register

            endpoint = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
            api_key = os.environ["PHOENIX_API_KEY"]
            register(
                project_name=os.getenv("PHOENIX_PROJECT_NAME", "granum"),
                endpoint=f"{endpoint}/v1/traces",
                headers={"api_key": api_key, "authorization": f"Bearer {api_key}"},
                batch=False,
                set_global_tracer_provider=True,
            )
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"WARN: Phoenix tracer registration failed: {exc}", err=True)

        _cell_rubric = Path(f"data/{cell}/judge_rubric.md")
        judge = LLMJudge(
            client=gemini,
            model=model,
            rubric_path=_cell_rubric
            if _cell_rubric.exists()
            else Path("data/judge_rubric.md"),
        )
        denial = generate_denial(payer=payer, diagnosis=diagnosis, seed=seed_value)
        typer.echo(
            f"Antigen {denial.denial_id} ({denial.denial_reason}); "
            f"evolving {generations} generations…"
        )
        typer.echo(
            f"  models: judge/appeal={model}  writer-mutator={resolve_mutator_model(model)}"
        )
        typer.echo(
            f"  selection: top-{survival_count} elitist survival, "
            f"{mutation_count} daughters/gen"
        )

        # Producer + API server agree on one location via GRANUM_DATA_DIR so the
        # frontend's poll reads the file this run is rewriting (live-grow).
        out_dir = Path(os.getenv("GRANUM_DATA_DIR", "runs/cell_payloads"))
        out_path = out_dir / f"{cell}.json"
        typer.echo(f"  live artifact (grows each generation): {out_path}")

        def _emit(partial) -> None:
            write_payload_atomic(out_path, partial.to_payload())

        async with phoenix_client_from_env() as phoenix:
            if reset:
                n = await reset_cell(phoenix, cell=cell)
                typer.echo(f"reset: hard-deleted {n} prompt(s) under {cell}")
            seeded = await seed_cell(phoenix, cell=cell)
            typer.echo(f"seeded {len(seeded)} gen-0 B-cells" if seeded else "cell already seeded")

            cyc = GerminalCycle(
                phoenix=phoenix,
                judge=judge,
                cell=cell,
                valid_citations_path=f"data/{cell}/valid_citations.json",
                gold_path=f"data/{cell}/gold_appeals.jsonl",
                mutation_proposer=propose_mutations,
                mutation_count=mutation_count,
                survival_count=survival_count,
                appeal_generator=gen_appeal,
                prompt_mutator=make_llm_mutator(
                    client=gemini,
                    model=resolve_mutator_model(model),
                    citation_hint=citation_hint_for_cell(cell),
                ),
                read_self_observability=True,  # Arize bonus: read own telemetry back
            )
            evolution = GenerationalEvolution(
                cycle=cyc, phoenix=phoenix, cell=cell, generations=generations
            )
            result = await evolution.run(denial=denial, progress_sink=_emit)

        payload = result.to_payload()
        write_payload_atomic(out_path, payload)  # final write with swept bodies

        typer.echo("")
        typer.echo("=== EVOLUTION COMPLETE (live) ===")
        for p in result.fitness_curve():
            typer.echo(
                f"  gen {p['generation']}: max={p['maxFitness']:.3f} "
                f"mean={p['meanFitness']:.3f} apoptosis={p['apoptosisCount']}"
            )
        typer.echo(
            f"  fitness: {payload['meta']['baselineOverturn']:.3f} -> "
            f"{payload['meta']['currentOverturn']:.3f}  |  "
            f"{payload['meta']['apoptosisTotal']} extinctions across "
            f"{len(payload['strategies'])} strategies"
        )
        typer.echo(f"  artifact: {out_path}")

    asyncio.run(_run())


@app.command()
def coevolve(
    cell: str = typer.Option("aetna_cardiac", "--cell", help="Cell id, e.g. aetna_cardiac"),
    rounds: int = typer.Option(8, "--rounds", help="Number of Red Queen rounds"),
    seed_value: int = typer.Option(42, "--seed-value", help="Deterministic antigen seed"),
    mutation_count: int = typer.Option(2, "--mutation-count", help="Mutations per winner per round"),
    reset: bool = typer.Option(
        False, "--reset", help="Hard-wipe + reseed the cell before running (clean slate)"
    ),
) -> None:
    """Run a live Red Queen co-evolution session for a cell.

    In each round the writer population (appeal drafters) faces the payer
    population (adversarial denial agents) in a triangular tournament scored
    by DefensibilityJudge. Losers are tombstoned in Phoenix, winners are
    promoted, and K clonal mutations are spawned in both populations so each
    side evolves against the other's improving counter-strategy.

    Writes runs/cell_payloads/{cell}_coevolution.json (the CoEvolutionState
    payload consumed by the frontend).

    Requires live Phoenix + Vertex Gemini auth (GOOGLE_CLOUD_PROJECT,
    PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT).
    """
    import asyncio
    import os
    from pathlib import Path

    required = ("GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        typer.echo(
            f"coevolve requires env: {', '.join(missing)}. Source .env first.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        payer, diagnosis = cell.split("_", 1)
    except ValueError:
        typer.echo(f"--cell must look like 'payer_diagnosis' (got {cell!r})", err=True)
        raise typer.Exit(code=2)

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

    from granum.adversary.payer_agent import PayerAgent
    from granum.center.coevolution import CoEvolutionDriver
    from granum.center.coevolution_run import CoEvolutionRun
    from granum.web.payload_io import write_payload_atomic
    from granum.center.defensibility_judge import DefensibilityJudge
    from granum.center.mutation_strategies import propose_mutations
    from granum.center.prompt_mutation import (
        citation_hint_for_cell,
        make_llm_mutator,
        resolve_mutator_model,
    )
    from granum.data.denials import Denial, generate_denial
    from granum.data.seeds import reset_cell, seed_cell, seed_payers, wait_for_active_population
    from granum.tools.gemini_client import GeminiClient
    from granum.tools.phoenix_session import phoenix_client_from_env

    gemini = GeminiClient()

    async def gen_appeal(system_prompt: str, denial: Denial) -> str:
        prompt = (
            f"{system_prompt}\n\n## Denial to appeal\n{denial.denial_text}\n\n"
            f"Payer: {denial.payer} | Diagnosis: {denial.diagnosis} | "
            f"CPT {denial.cpt_code} | ICD-10 {denial.icd10_code} | "
            f"Patient age {denial.patient_age_range} | "
            f"Appeal deadline {denial.appeal_deadline_days} days.\n\n"
            "Write the complete appeal letter now. Output only the letter."
        )
        return await gemini.generate(model=model, prompt=prompt, temperature=0.3)

    async def _run() -> None:
        try:
            from phoenix.otel import register

            endpoint = os.environ["PHOENIX_COLLECTOR_ENDPOINT"].rstrip("/")
            api_key = os.environ["PHOENIX_API_KEY"]
            register(
                project_name=os.getenv("PHOENIX_PROJECT_NAME", "granum"),
                endpoint=f"{endpoint}/v1/traces",
                headers={"api_key": api_key, "authorization": f"Bearer {api_key}"},
                batch=False,
                set_global_tracer_provider=True,
            )
        except Exception as exc:  # noqa: BLE001 — tracing is supplementary
            typer.echo(f"WARN: Phoenix tracer registration failed: {exc}", err=True)

        judge = DefensibilityJudge(
            client=gemini, model=model, rubric_path=Path("data/defensibility_rubric.md")
        )
        payer_agent = PayerAgent(client=gemini, model=model, payer=payer, diagnosis=diagnosis)
        # Shared antigen all writers draft a real appeal against this run.
        antigen = generate_denial(payer=payer, diagnosis=diagnosis, seed=seed_value)
        typer.echo(
            f"Antigen {antigen.denial_id} ({antigen.denial_reason}); "
            f"co-evolving {rounds} rounds…"
        )
        typer.echo(
            f"  models: judge/payer/appeal={model}  writer-mutator={resolve_mutator_model(model)}"
        )

        async with phoenix_client_from_env() as phoenix:
            if reset:
                n = await reset_cell(phoenix, cell=cell)
                typer.echo(f"reset: hard-deleted {n} prompt(s) under {cell}")
            seeded_writers = await seed_cell(phoenix, cell=cell)
            typer.echo(
                f"seeded {len(seeded_writers)} gen-0 writers"
                if seeded_writers
                else "writers already seeded"
            )
            seeded_payers = await seed_payers(phoenix, cell=cell)
            typer.echo(
                f"seeded {len(seeded_payers)} gen-0 payers"
                if seeded_payers
                else "payers already seeded"
            )

            await wait_for_active_population(phoenix, name_prefix=f"{cell}/", min_count=1)
            await wait_for_active_population(phoenix, name_prefix=f"{cell}_payer/", min_count=1)
            typer.echo("populations ready")

            driver = CoEvolutionDriver(
                phoenix=phoenix,
                payer_agent=payer_agent,
                judge=judge,
                cell=cell,
                gold_path=f"data/{cell}/gold_appeals.jsonl",
                mutation_proposer=propose_mutations,
                mutation_count=mutation_count,
                appeal_generator=gen_appeal,
                antigen=antigen,
                prompt_mutator=make_llm_mutator(
                    client=gemini,
                    model=resolve_mutator_model(model),
                    citation_hint=citation_hint_for_cell(cell),
                ),
            )
            out_dir = Path(os.getenv("GRANUM_DATA_DIR", "runs/cell_payloads"))
            artifact = out_dir / f"{cell}_coevolution.json"
            typer.echo(f"  live artifact (grows each round): {artifact}")

            def _emit(partial) -> None:
                write_payload_atomic(artifact, partial.to_payload())

            run = CoEvolutionRun(driver=driver, phoenix=phoenix, cell=cell, rounds=rounds)
            result = await run.run(progress_sink=_emit)

        payload = result.to_payload()
        write_payload_atomic(artifact, payload)  # final write with swept bodies

        writers = payload.get("writers", [])
        payers = payload.get("payers", [])
        writer_champion = next(
            (w for w in writers if w.get("status") == "champion"), None
        )
        payer_champion = next(
            (p for p in payers if p.get("status") == "champion"), None
        )

        typer.echo("")
        typer.echo("=== CO-EVOLUTION COMPLETE (live) ===")
        typer.echo(
            f"  writers: {len(writers)} total  |  payers: {len(payers)} total"
        )
        if writer_champion:
            typer.echo(
                f"  writer champion: {writer_champion['id']} "
                f"(fitness {writer_champion['fitness']:.4f})"
            )
        if payer_champion:
            typer.echo(
                f"  payer champion:  {payer_champion['id']} "
                f"(fitness {payer_champion['fitness']:.4f})"
            )
        typer.echo(f"  artifact: {artifact}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
