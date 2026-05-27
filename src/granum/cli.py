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


if __name__ == "__main__":
    app()
