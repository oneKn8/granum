"""Atomic payload writes for live-grow.

During a live ``granum evolve`` / ``granum coevolve`` run the runner rewrites
``{cell}.json`` after every generation/round, while the FastAPI server reads the
same file on each poll (``cache: "no-store"`` from the frontend). A naive
``open(..., "w")`` would let a poll land mid-write and read a truncated /
half-serialized file, 500-ing the demo. ``write_payload_atomic`` serializes to a
temp file in the SAME directory, then ``os.replace`` renames it over the target —
an atomic operation on POSIX, so a reader sees either the old file or the new
one, never a partial one.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_payload_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    """Atomically write ``payload`` as pretty JSON to ``path``.

    Creates parent directories as needed. On any failure the temp file is
    removed so no ``.tmp`` litter is left for the next reader to trip over.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
