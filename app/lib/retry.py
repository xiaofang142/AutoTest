import asyncio
import logging
import random
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RetryConfig:
    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True


async def with_retry(
    func: Callable,
    config: Optional[RetryConfig] = None,
    context: Optional[dict] = None,
) -> Any:
    if config is None:
        config = RetryConfig()
    last_exception = None
    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = min(
                    config.base_delay_s * (config.backoff_factor**attempt),
                    config.max_delay_s,
                )
                if config.jitter:
                    delay *= random.uniform(0.8, 1.2)
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_retries} after {delay:.1f}s",
                    extra={"context": context or {}},
                )
                await asyncio.sleep(delay)
    raise last_exception
