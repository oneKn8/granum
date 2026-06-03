"""Vertex Gemini generation client — the real `_GenClient` for the germinal loop.

One client backs BOTH:
  - the LLM-as-judge (`json_mode=True` → strict JSON scores), and
  - appeal drafting (prose).

The google-genai SDK call is synchronous, so we run it in a worker thread via
`asyncio.to_thread`. That keeps `generate()` a true coroutine — the judge fires
three concurrent samples with `asyncio.gather` and they actually overlap rather
than serialize.

Env (Vertex mode, set in `.env`):
- GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI=true
"""
from __future__ import annotations

import asyncio
import os

from google import genai
from google.genai import types


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

    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        config = types.GenerateContentConfig(temperature=temperature)
        if json_mode:
            config.response_mime_type = "application/json"

        def _call() -> str:
            resp = self._client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return (resp.text or "").strip()

        return await asyncio.to_thread(_call)
