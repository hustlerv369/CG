"""retry decorator — Opus 4.7's output from run d7577ba1f20b, verbatim.

Sonnet's critique: "Implementation is correct against the spec."

Spec (compressed):
    @retry(max_attempts=3, base_delay=0.1, max_delay=10.0,
           exceptions=(Exception,), jitter=True)
    - Sync OR async functions
    - delay = min(base_delay * 2^(retry_num - 1), max_delay)
    - jitter=True → uniform(0, delay)
    - exception not in tuple → propagate immediately
    - last attempt fails → re-raise original
    - max_attempts <= 0 → ValueError at decoration time
"""

import asyncio
import functools
import inspect  # noqa: F401  (left in to match original spec output)
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
    exceptions: tuple = (Exception,),
    jitter: bool = True,
):
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
        raise TypeError("max_attempts must be an int")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be >= 1")
    if not isinstance(exceptions, tuple):
        raise TypeError("exceptions must be a tuple")
    if len(exceptions) == 0:
        raise ValueError("exceptions tuple must be non-empty")
    for exc in exceptions:
        if not (isinstance(exc, type) and issubclass(exc, BaseException)):
            raise TypeError(
                "exceptions tuple must contain only BaseException subclasses")
    if base_delay < 0.0:
        raise ValueError("base_delay must be >= 0.0")
    if max_delay < base_delay:
        raise ValueError("max_delay must be >= base_delay")

    def _compute_sleep(retry_num: int) -> float:
        delay = min(base_delay * (2 ** (retry_num - 1)), max_delay)
        if jitter:
            return random.uniform(0, delay)
        return delay

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                attempt = 1
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except BaseException as exc:
                        if not isinstance(exc, exceptions):
                            raise
                        if attempt >= max_attempts:
                            raise
                        sleep_for = _compute_sleep(attempt)
                        await asyncio.sleep(sleep_for)
                        attempt += 1
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            attempt = 1
            while True:
                try:
                    return func(*args, **kwargs)
                except BaseException as exc:
                    if not isinstance(exc, exceptions):
                        raise
                    if attempt >= max_attempts:
                        raise
                    sleep_for = _compute_sleep(attempt)
                    time.sleep(sleep_for)
                    attempt += 1
        return sync_wrapper

    return decorator
