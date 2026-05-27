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


if __name__ == "__main__":
    app()
