"""Unit tests for feedback-directed prompt mutation (mocked client, no live cost)."""
from unittest.mock import AsyncMock

import pytest

from granum.center.prompt_mutation import make_llm_mutator


@pytest.mark.asyncio
async def test_parses_variants_and_passes_feedback_in_prompt():
    client = AsyncMock()
    client.generate.return_value = (
        '[{"strategy": "improved A", "change": "tighter citations"},'
        ' {"strategy": "improved B", "change": "more evidence"}]'
    )
    mutate = make_llm_mutator(client=client, model="gemini-3.1-pro-preview")

    out = await mutate("parent strategy body", "appeal lacked section-level citations", 2)

    assert out == [("improved A", "tighter citations"), ("improved B", "more evidence")]
    kwargs = client.generate.call_args.kwargs
    assert kwargs["json_mode"] is True
    assert "appeal lacked section-level citations" in kwargs["prompt"]
    assert "parent strategy body" in kwargs["prompt"]


@pytest.mark.asyncio
async def test_tolerates_json_fences():
    client = AsyncMock()
    client.generate.return_value = '```json\n[{"strategy": "X", "change": "y"}]\n```'
    mutate = make_llm_mutator(client=client, model="m")
    assert await mutate("p", "f", 1) == [("X", "y")]


@pytest.mark.asyncio
async def test_skips_empty_strategy_and_defaults_note():
    client = AsyncMock()
    client.generate.return_value = (
        '[{"strategy": "", "change": "dropped"}, {"strategy": "kept", "change": ""}]'
    )
    mutate = make_llm_mutator(client=client, model="m")
    assert await mutate("p", "f", 2) == [("kept", "feedback-directed revision")]


@pytest.mark.asyncio
async def test_empty_feedback_uses_placeholder():
    client = AsyncMock()
    client.generate.return_value = '[{"strategy": "s", "change": "c"}]'
    mutate = make_llm_mutator(client=client, model="m")
    await mutate("parent", "", 1)
    assert "(no critique available)" in client.generate.call_args.kwargs["prompt"]
