"""Vertex Gemini generation client — the real `_GenClient` for the germinal loop.

One client backs BOTH:
  - the LLM-as-judge (`json_mode=True` → strict JSON scores), and
  - appeal drafting (prose).

The google-genai SDK call is synchronous, so we run it in a worker thread via
`asyncio.to_thread`. That keeps `generate()` a true coroutine — the judge fires
three concurrent samples with `asyncio.gather` and they actually overlap rather
than serialize.

Concurrency + reliability:
  - `self._sem` caps simultaneous in-flight Gemini calls to `GRANUM_GEMINI_CONCURRENCY`
    (default 5). This prevents the nested asyncio.gather bursts that triggered
    429 RESOURCE_EXHAUSTED on Vertex during tournament co-evolution runs.
  - `generate()` retries on 429 (rate limited) and 503 (transient unavailable)
    with exponential backoff (base * 2^attempt, capped at max_backoff). The
    semaphore is held across the backoff sleep to add natural backpressure.

Env (Vertex mode, set in `.env`):
- GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI=true
- GRANUM_GEMINI_CONCURRENCY   (int, default 5)
- GRANUM_GEMINI_MAX_ATTEMPTS  (int, default 6)
- GRANUM_GEMINI_BASE_BACKOFF  (float seconds, default 2.0)
- GRANUM_GEMINI_MAX_BACKOFF   (float seconds, default 60.0)
"""
from __future__ import annotations

import asyncio
import os

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# HTTP status codes that are transient and worth retrying.
_RETRYABLE_CODES = frozenset({429, 503})


class GeminiClient:
    """Thin async wrapper over `google.genai` (Vertex) matching the `_GenClient` protocol."""

    def __init__(
        self,
        *,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT not set — cannot reach Vertex.")
        self._client = genai.Client(vertexai=True, project=project, location=location)

        # Concurrency cap: guards against flooding Vertex with too many parallel calls.
        _concurrency = int(os.getenv("GRANUM_GEMINI_CONCURRENCY", "5"))
        self._sem = asyncio.Semaphore(_concurrency)

        # Retry knobs for 429/503 backoff.
        self._max_attempts = int(os.getenv("GRANUM_GEMINI_MAX_ATTEMPTS", "6"))
        self._base_backoff = float(os.getenv("GRANUM_GEMINI_BASE_BACKOFF", "2.0"))
        self._max_backoff = float(os.getenv("GRANUM_GEMINI_MAX_BACKOFF", "60.0"))

    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        # Concurrency cap + backoff-retry guard against Vertex 429s.
        # The semaphore is held across backoff sleeps for natural backpressure.
        config = types.GenerateContentConfig(temperature=temperature)
        if json_mode:
            config.response_mime_type = "application/json"

        def _call() -> str:
            resp = self._client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return (resp.text or "").strip()

        last_exc: genai_errors.APIError | None = None
        async with self._sem:
            for attempt in range(self._max_attempts):
                try:
                    return await asyncio.to_thread(_call)
                except genai_errors.APIError as exc:
                    if getattr(exc, "code", None) in _RETRYABLE_CODES:
                        last_exc = exc
                        if attempt < self._max_attempts - 1:
                            backoff = min(
                                self._base_backoff * (2**attempt), self._max_backoff
                            )
                            await asyncio.sleep(backoff)
                            continue
                        # Final attempt exhausted — fall through to re-raise.
                        raise
                    # Non-retryable error: re-raise immediately.
                    raise

        # Should be unreachable, but satisfies the type checker.
        raise last_exc  # type: ignore[misc]
