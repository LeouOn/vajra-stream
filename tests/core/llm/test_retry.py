# tests/core/llm/test_retry.py
import pytest

from core.llm.retry import retry_with_backoff


@pytest.mark.asyncio
async def test_retry_success_first_try():
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_success_after_failure():
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("transient")
        return "ok"

    result = await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted():
    async def fn():
        raise RuntimeError("permanent")

    with pytest.raises(RuntimeError, match="permanent"):
        await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
