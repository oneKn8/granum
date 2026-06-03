"""Tests for granum.tools.json_parse.loads_lenient."""
from __future__ import annotations

import json
import pytest

from granum.tools.json_parse import loads_lenient


def test_loads_lenient_bare_json() -> None:
    """Bare JSON object parses correctly."""
    result = loads_lenient('{"a": 1}')
    assert result == {"a": 1}


def test_loads_lenient_fenced_json() -> None:
    """JSON wrapped in ```json ... ``` fences parses correctly."""
    raw = '```json\n{"a": 1}\n```'
    result = loads_lenient(raw)
    assert result == {"a": 1}


def test_loads_lenient_prose_then_json_then_prose() -> None:
    """JSON embedded in surrounding prose parses correctly."""
    raw = 'Here is the result:\n{"a": 1}\nEnd of output.'
    result = loads_lenient(raw)
    assert result == {"a": 1}


def test_loads_lenient_nested_object() -> None:
    """Nested JSON object parses correctly."""
    raw = '```json\n{"x": {"y": 2}, "z": [1, 2]}\n```'
    result = loads_lenient(raw)
    assert result == {"x": {"y": 2}, "z": [1, 2]}


def test_loads_lenient_raises_on_garbage() -> None:
    """Non-JSON content raises json.JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        loads_lenient("no json here at all")
