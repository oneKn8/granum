"""Tests for GeminiClient concurrency cap + exponential backoff-retry on 429/503.

TDD: these tests are written before the implementation changes. They should
fail on the current code and pass once the implementation is updated.

APIError construction: `APIError(code, response_json, response=None)`.
`ClientError` and `ServerError` are subclasses — we use `ClientError` for 4xx
and `ServerError` for 5xx, consistent with how google.genai raises them live.
Both are `isinstance(e, genai_errors.APIError)`, so our `except APIError` clause
catches them; we then check `.code` to decide retryability.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from google.genai import errors as genai_errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_error(code: int) -> genai_errors.APIError:
    """Build an APIError (or appropriate subclass) with the given HTTP status code.

    We use ClientError for 4xx and ServerError for 5xx so the instance is
    identical to what the live SDK raises. In all cases isinstance(e, APIError)
    is True, and e.code == code.
    """
    body = {"error": {"code": code, "message": "test error", "status": "TEST_STATUS"}}
    if 400 <= code < 500:
        return genai_errors.ClientError(code, body)
    elif 500 <= code < 600:
        return genai_errors.ServerError(code, body)
    return genai_errors.APIError(code, body)


# ---------------------------------------------------------------------------
# Fixtures / shared patching
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_env(monkeypatch):
    """Ensure GOOGLE_CLOUD_PROJECT is set so GeminiClient.__init__ doesn't raise."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    # Reset concurrency/retry knobs to defaults so tests are predictable.
    monkeypatch.delenv("GRANUM_GEMINI_CONCURRENCY", raising=False)
    monkeypatch.delenv("GRANUM_GEMINI_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("GRANUM_GEMINI_BASE_BACKOFF", raising=False)
    monkeypatch.delenv("GRANUM_GEMINI_MAX_BACKOFF", raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_generate_retries_on_429_then_succeeds(patched_env):
    """Underlying call raises 429 twice, then succeeds on the 3rd attempt.

    Asserts:
    - generate() returns the successful response text
    - generate_content was called exactly 3 times
    - asyncio.sleep was called twice (once per failed attempt, not on success)
    """
    success_response = MagicMock()
    success_response.text = "ok"

    err_429 = _make_api_error(429)

    with patch("granum.tools.gemini_client.genai.Client") as mock_genai_client, \
         patch("granum.tools.gemini_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        # Set up the underlying sync generate_content call: fail, fail, succeed.
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = [err_429, err_429, success_response]
        mock_genai_client.return_value.models = mock_models

        from granum.tools.gemini_client import GeminiClient
        client = GeminiClient()

        result = await client.generate(model="m", prompt="p")

    assert result == "ok"
    assert mock_models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


async def test_generate_reraises_non_retryable_error(patched_env):
    """A 400 APIError is not retryable — re-raised immediately after first attempt."""
    err_400 = _make_api_error(400)

    with patch("granum.tools.gemini_client.genai.Client") as mock_genai_client, \
         patch("granum.tools.gemini_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        mock_models = MagicMock()
        mock_models.generate_content.side_effect = err_400
        mock_genai_client.return_value.models = mock_models

        from granum.tools.gemini_client import GeminiClient
        client = GeminiClient()

        with pytest.raises(genai_errors.APIError) as exc_info:
            await client.generate(model="m", prompt="p")

    assert exc_info.value.code == 400
    assert mock_models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


async def test_generate_gives_up_after_max_attempts(monkeypatch):
    """Always-429 exhausts all attempts and re-raises the last exception."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GRANUM_GEMINI_MAX_ATTEMPTS", "3")
    monkeypatch.delenv("GRANUM_GEMINI_CONCURRENCY", raising=False)
    monkeypatch.delenv("GRANUM_GEMINI_BASE_BACKOFF", raising=False)
    monkeypatch.delenv("GRANUM_GEMINI_MAX_BACKOFF", raising=False)

    err_429 = _make_api_error(429)

    with patch("granum.tools.gemini_client.genai.Client") as mock_genai_client, \
         patch("granum.tools.gemini_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        mock_models = MagicMock()
        mock_models.generate_content.side_effect = err_429
        mock_genai_client.return_value.models = mock_models

        # Import AFTER env vars are set so __init__ reads the new values.
        import importlib
        import granum.tools.gemini_client as gc_mod
        importlib.reload(gc_mod)
        GeminiClient = gc_mod.GeminiClient

        client = GeminiClient()

        with pytest.raises(genai_errors.APIError) as exc_info:
            await client.generate(model="m", prompt="p")

    assert exc_info.value.code == 429
    # 3 attempts total; sleep called on the first 2 failures (not after the last)
    assert mock_models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


async def test_generate_503_is_retryable(patched_env):
    """503 (transient server error) is also retried, not just 429."""
    success_response = MagicMock()
    success_response.text = "recovered"

    err_503 = _make_api_error(503)

    with patch("granum.tools.gemini_client.genai.Client") as mock_genai_client, \
         patch("granum.tools.gemini_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        mock_models = MagicMock()
        mock_models.generate_content.side_effect = [err_503, success_response]
        mock_genai_client.return_value.models = mock_models

        from granum.tools.gemini_client import GeminiClient
        client = GeminiClient()

        result = await client.generate(model="m", prompt="p")

    assert result == "recovered"
    assert mock_models.generate_content.call_count == 2
    assert mock_sleep.call_count == 1


async def test_semaphore_limits_concurrency(patched_env, monkeypatch):
    """Concurrency cap is respected: with cap=2 only 2 calls run at once.

    We patch asyncio.to_thread to an async function so it runs in-loop.
    The fake returns a plain string (what _call() would return) so the outer
    generate() can return it unchanged.
    """
    import asyncio as real_asyncio

    monkeypatch.setenv("GRANUM_GEMINI_CONCURRENCY", "2")

    concurrent_count = 0
    max_concurrent = 0

    async def fake_thread_call(fn, *args, **kwargs):
        """Pretend to be asyncio.to_thread: run fn() inline but track concurrency."""
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        if concurrent_count > max_concurrent:
            max_concurrent = concurrent_count
        await real_asyncio.sleep(0)  # yield so other coroutines can enter
        concurrent_count -= 1
        # Return what _call() would return: a plain string.
        return "done"

    with patch("granum.tools.gemini_client.genai.Client") as mock_genai_client:
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(text="done")
        mock_genai_client.return_value.models = mock_models

        import importlib
        import granum.tools.gemini_client as gc_mod
        importlib.reload(gc_mod)
        GeminiClient = gc_mod.GeminiClient

        client = GeminiClient()

        with patch("granum.tools.gemini_client.asyncio.to_thread", side_effect=fake_thread_call):
            tasks = [client.generate(model="m", prompt="p") for _ in range(5)]
            results = await real_asyncio.gather(*tasks)

    assert results == ["done"] * 5
    # With semaphore cap=2, at most 2 fake_thread_call bodies run concurrently.
    assert max_concurrent <= 2
