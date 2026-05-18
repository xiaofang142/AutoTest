import pytest

from app.lib.retry import RetryConfig, with_retry


class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay_s == 1.0
        assert cfg.max_delay_s == 30.0
        assert cfg.backoff_factor == 2.0
        assert cfg.jitter is True


def _make_config(max_retries=3, base_delay_s=1.0, max_delay_s=30.0, backoff_factor=2.0, jitter=True):
    cfg = RetryConfig()
    cfg.max_retries = max_retries
    cfg.base_delay_s = base_delay_s
    cfg.max_delay_s = max_delay_s
    cfg.backoff_factor = backoff_factor
    cfg.jitter = jitter
    return cfg


@pytest.mark.asyncio
class TestWithRetry:
    async def test_success_on_first_try(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await with_retry(succeed)
        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_failure(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        config = _make_config(max_retries=3, base_delay_s=0.01, jitter=False)
        result = await with_retry(fail_then_succeed, config)
        assert result == "success"
        assert call_count == 3

    async def test_raises_after_exhausted_retries(self):
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        config = _make_config(max_retries=2, base_delay_s=0.01, jitter=False)
        with pytest.raises(ValueError, match="Persistent failure"):
            await with_retry(always_fail, config)
        assert call_count == 3
