"""Seed a (payer × diagnosis) cell with its gen-0 B-cell strategies.

Thin CLI wrapper over `granum.data.seeds` (the single source of truth for the
seed bank, shared with `granum evolve`).

Usage:
    cd granum/
    set -a; source .env; set +a
    source ~/.nvm/nvm.sh && nvm use default
    env -u PYTHONPATH uv run python scripts/seed_cell.py --cell aetna_cardiac
"""
from __future__ import annotations

import asyncio

import typer

from granum.data.seeds import SEED_BANK, seed_cell
from granum.tools.phoenix_session import phoenix_client_from_env

app = typer.Typer()


@app.command()
def main(
    cell: str = typer.Option("aetna_cardiac", "--cell", help="Cell id to seed"),
) -> None:
    """Seed a cell with its gen-0 B-cell strategies, tagged production."""
    if cell not in SEED_BANK:
        typer.echo(
            f"No seed bank for cell {cell!r}. Available: {', '.join(SEED_BANK)}",
            err=True,
        )
        raise typer.Exit(code=2)
    asyncio.run(_seed(cell=cell))


async def _seed(*, cell: str) -> None:
    async with phoenix_client_from_env() as phoenix:
        ids = await seed_cell(phoenix, cell=cell)
        if not ids:
            typer.echo(
                f"Cell {cell} already has active prompts. Skipping seed "
                f"(reset first to reseed)."
            )
            return
        for pid in ids:
            typer.echo(f"seeded {pid}")
        typer.echo(f"Seeded {len(ids)} B-cells in cell {cell}.")


if __name__ == "__main__":
    app()
