"""Vertex Gemini smoke — confirms Vertex access + model availability.

Usage:
    export GOOGLE_CLOUD_PROJECT=<project_id>
    export GOOGLE_CLOUD_LOCATION=global   # recommended for current Gemini 3 models
    uv run python scripts/smoke_gemini.py

Model fallback chain (verified 2026-05-27 against Vertex AI):
    1. gemini-3.1-pro-preview  — primary reasoning, public preview since Feb 2026
    2. gemini-3.5-flash         — released Google I/O 2026 (May 19), fast tier
    3. gemini-2.5-pro           — last-resort fallback if 3.x unavailable

NOTE: `gemini-3-pro` was DISCONTINUED in March 2026 and is intentionally NOT
in this list. See research/gcp-rapid-agent-2026.md + feedback memory
`feedback-verify-model-names-and-apis` for the discovery story.
"""

from __future__ import annotations

import os
import sys

from google import genai


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    if not project:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set", file=sys.stderr)
        return 2

    client = genai.Client(vertexai=True, project=project, location=location)

    candidates = ["gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-2.5-pro"]
    last_err: Exception | None = None
    for model in candidates:
        try:
            resp = client.models.generate_content(
                model=model,
                contents="Reply with exactly one word: alive.",
            )
            text = (resp.text or "").strip()
            print(f"model={model} location={location} response={text!r}")
            return 0
        except Exception as exc:  # noqa: BLE001 — smoke test is intentionally broad
            last_err = exc
            print(f"model={model} failed: {exc}", file=sys.stderr)

    print(f"All models failed; last error: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
