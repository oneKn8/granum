"""Phoenix Cloud smoke — emit a single trace and confirm export pipeline.

Usage:
    export PHOENIX_API_KEY=<key>
    export PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
    export PHOENIX_PROJECT_NAME=granum   # optional, defaults to 'granum'
    uv run python scripts/smoke_phoenix.py

Then verify the span 'granum.smoke' appears in the Phoenix UI under the
configured project.
"""

from __future__ import annotations

import os
import sys
import time

from phoenix.otel import register


def main() -> int:
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    api_key = os.environ.get("PHOENIX_API_KEY")
    project = os.environ.get("PHOENIX_PROJECT_NAME", "granum")

    if not endpoint:
        print("ERROR: PHOENIX_COLLECTOR_ENDPOINT not set", file=sys.stderr)
        return 2
    if not api_key:
        print("ERROR: PHOENIX_API_KEY not set", file=sys.stderr)
        return 2

    tracer_provider = register(
        project_name=project,
        endpoint=f"{endpoint.rstrip('/')}/v1/traces",
        headers={"api_key": api_key, "authorization": f"Bearer {api_key}"},
        batch=False,
    )
    tracer = tracer_provider.get_tracer(__name__)

    with tracer.start_as_current_span("granum.smoke") as span:
        span.set_attribute("granum.smoke.kind", "phase-0.4")
        span.set_attribute("granum.smoke.user", os.environ.get("USER", "dev"))
        span.set_attribute("granum.smoke.ts", time.time())

    # Force flush so the script exit doesn't drop the span on the floor.
    try:
        tracer_provider.force_flush(timeout_millis=5000)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: force_flush failed: {exc}", file=sys.stderr)

    print(
        f"OK — trace emitted to {endpoint} (project={project}). "
        "Verify span 'granum.smoke' in the Phoenix UI."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
