"""Vertex Gemini smoke — confirms Vertex access + model availability.

Usage:
    export GOOGLE_CLOUD_PROJECT=<project_id>
    export GOOGLE_CLOUD_LOCATION=us-central1
    uv run python scripts/smoke_gemini.py

Falls back from gemini-3-pro to gemini-2.5-pro if the primary model is
unavailable (region lock or quota).
"""

from __future__ import annotations

import os
import sys

from google import genai


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set", file=sys.stderr)
        return 2

    client = genai.Client(vertexai=True, project=project, location=location)

    candidates = ["gemini-3-pro", "gemini-2.5-pro"]
    last_err: Exception | None = None
    for model in candidates:
        try:
            resp = client.models.generate_content(
                model=model,
                contents="Reply with exactly one word: alive.",
            )
            text = (resp.text or "").strip()
            print(f"model={model} response={text!r}")
            return 0
        except Exception as exc:  # noqa: BLE001 — smoke test is intentionally broad
            last_err = exc
            print(f"model={model} failed: {exc}", file=sys.stderr)

    print(f"All models failed; last error: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
