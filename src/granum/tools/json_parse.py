"""Lenient JSON parser that tolerates ```json fences and surrounding prose."""
from __future__ import annotations

import json
from typing import Any


def loads_lenient(raw: str) -> Any:
    """Parse model JSON, tolerating ```json fences / prose around the object."""
    text = raw.strip()
    if text.startswith("```"):
        # ```json\n{...}\n```  -> drop the fence lines
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
