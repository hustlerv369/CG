"""Adversarial test suite for the retry decorator from run d7577ba1f20b.

Sonnet's critique said "implementation is correct against the spec".
This file actually exercises every spec bullet so we don't take that
on faith.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from examples.retry_decorator import retry


# ---- decoration-time validation -------------------------------------


def test_max_attempts_zero_raises():
    with pytest.raises(ValueError):
        retry(max_attempts=0)


def test_max_attempts_negative_raises():
    with pytest.raises(ValueError):
        retry(max_attempts=-1)


def test_max_attempts_bool_raises_type_error():
    """bool is a subclass of int — guard explicitly rejects it."""
    with pytest.raises(TypeError):
        retry(max_attempts=True)  # type: ignore[arg-type]


def test_exceptions_must_be_tuple():
    with pytest.raises(TypeError):
        retry(exceptions=Exception)  # type: ignore[arg-type]


def test_empty_exceptions_tuple_raises():
    with pytest.raises(ValueError):
        retry(exceptions=())


def test_exceptions_tuple_non_class_raises():
    with pytest.raises(TypeError):
        retry(exceptions=(ValueError, "not a class"))  # type: ignore[arg-type]


def test_base_delay_negative_raises():
    with pytest.raises(ValueError):
        retry(base_delay=-0.5)


def test_max_delay_smaller_than_base_raises():
    with pytest.raises(ValueError):
        retry(base_delay=1.0, max_delay=0.5)


# ---- runtime behaviour ----------------------------------------------


def test_success_on_first_try_no_retry():
    calls = []

    @retry(max_attempts=3, base_delay=0.0, jitter=False)
    def fn():
        calls.append(1)
        return "ok"

    assert fn() == "ok"
    assert len(calls) == 1


def test_retry_until_success(monkeypatch):
    """Function fails twice, succeeds third time → returns the value."""
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    calls = []

    @retry(max_attempts=5, base_delay=0.0, jitter=False)
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")
        return 42

    assert fn() == 42
    assert len(calls) == 3


def test_exhaust_attempts_reraises_last_exception(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    calls = []

    @retry(max_attempts=3, base_delay=0.0, jitter=False)
    def fn():
        calls.append(1)
        raise RuntimeError(f"boom-{len(calls)}")

    with pytest.raises(RuntimeError, match="boom-3"):
        fn()
    assert len(calls) == 3


def test_exception_not_in_tuple_propagates_immediately(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    calls = []

    @retry(max_attempts=5, base_delay=0.0, jitter=False,
           exceptions=(ValueError,))
    def fn():
        calls.append(1)
        raise RuntimeError("not a ValueError")

    with pytest.raises(RuntimeError):
        fn()
    assert len(calls) == 1, "should NOT retry on excluded exception"


def test_exponential_backoff_no_jitter(monkeypatch):
    """delay = min(base * 2^(n-1), max). With jitter=False the call to
    time.sleep gets the exact computed delay each time."""
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))
    calls = []

    @retry(max_attempts=4, base_delay=0.5, max_delay=10.0, jitter=False)
    def fn():
        calls.append(1)
        if len(calls) < 4:
            raise RuntimeError("boom")
        return "ok"

    assert fn() == "ok"
    assert sleeps == [0.5, 1.0, 2.0]  # 3 retries before the 4th succeeds


def test_max_delay_caps_backoff(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))
    calls = []

    @retry(max_attempts=6, base_delay=1.0, max_delay=3.0, jitter=False)
    def fn():
        calls.append(1)
        if len(calls) < 6:
            raise RuntimeError("boom")
        return "ok"

    assert fn() == "ok"
    # base * 2^(n-1) → 1, 2, 4, 8, 16  → capped to max_delay=3.0
    assert sleeps == [1.0, 2.0, 3.0, 3.0, 3.0]


def test_jitter_stays_within_bounds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))
    calls = []

    @retry(max_attempts=4, base_delay=1.0, max_delay=10.0, jitter=True)
    def fn():
        calls.append(1)
        if len(calls) < 4:
            raise RuntimeError("boom")
        return "ok"

    fn()
    # With jitter every sleep ∈ [0, computed_delay]
    assert all(0.0 <= s <= 4.0 for s in sleeps)
    assert sleeps[0] <= 1.0
    assert sleeps[1] <= 2.0
    assert sleeps[2] <= 4.0


def test_preserves_wrapped_metadata():
    @retry(max_attempts=3)
    def widget(a: int, b: int = 7) -> int:
        """do stuff"""
        return a + b

    assert widget.__name__ == "widget"
    assert widget.__doc__ == "do stuff"


# ---- async support --------------------------------------------------


def test_async_function_retries_until_success(monkeypatch):
    async def _no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    calls = []

    @retry(max_attempts=4, base_delay=0.0, jitter=False)
    async def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")
        return "async-ok"

    result = asyncio.run(fn())
    assert result == "async-ok"
    assert len(calls) == 3


def test_async_function_propagates_excluded_exception(monkeypatch):
    async def _no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    calls = []

    @retry(max_attempts=5, base_delay=0.0, jitter=False,
           exceptions=(ValueError,))
    async def fn():
        calls.append(1)
        raise RuntimeError("not a ValueError")

    with pytest.raises(RuntimeError):
        asyncio.run(fn())
    assert len(calls) == 1
