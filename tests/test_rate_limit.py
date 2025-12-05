"""Tests for rate limiting module."""

from __future__ import annotations

import pytest

from kepler_mcp_gitlab.config import Config
from kepler_mcp_gitlab.rate_limit import (
    RateLimiter,
    RateLimitError,
    TokenBucket,
    create_rate_limiter,
)


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_initial_tokens(self) -> None:
        """Test initial token count."""
        bucket = TokenBucket(capacity=10.0, tokens=10.0, fill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_success(self) -> None:
        """Test successful token consumption."""
        bucket = TokenBucket(capacity=10.0, tokens=10.0, fill_rate=1.0)
        assert bucket.consume() is True
        assert bucket.tokens < 10.0

    def test_consume_failure(self) -> None:
        """Test failed consumption when no tokens."""
        bucket = TokenBucket(capacity=10.0, tokens=0.0, fill_rate=1.0)
        assert bucket.consume() is False

    def test_time_until_available(self) -> None:
        """Test time calculation for token availability."""
        bucket = TokenBucket(capacity=10.0, tokens=0.0, fill_rate=1.0)
        wait_time = bucket.time_until_available()
        assert wait_time > 0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_try_acquire_success(self) -> None:
        """Test successful non-blocking acquire."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        assert limiter.try_acquire() is True

    def test_try_acquire_exhausts_burst(self) -> None:
        """Test that burst capacity is exhausted."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)

        # Exhaust burst
        for _ in range(5):
            assert limiter.try_acquire() is True

        # Next request should fail
        assert limiter.try_acquire() is False

    def test_per_key_isolation(self) -> None:
        """Test that keys are isolated."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)

        # Exhaust key1
        assert limiter.try_acquire("key1") is True
        assert limiter.try_acquire("key1") is True
        assert limiter.try_acquire("key1") is False

        # key2 should still work
        assert limiter.try_acquire("key2") is True

    def test_get_retry_after(self) -> None:
        """Test retry-after calculation."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)

        # Exhaust burst
        limiter.try_acquire()

        # Should have non-zero retry time
        retry_after = limiter.get_retry_after()
        assert retry_after > 0

    def test_reset_specific_key(self) -> None:
        """Test resetting a specific key."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)

        # Exhaust key1
        limiter.try_acquire("key1")
        assert limiter.try_acquire("key1") is False

        # Reset key1
        limiter.reset("key1")
        assert limiter.try_acquire("key1") is True

    def test_reset_all(self) -> None:
        """Test resetting all keys."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)

        # Exhaust multiple keys
        limiter.try_acquire("key1")
        limiter.try_acquire("key2")

        # Reset all
        limiter.reset()

        # Both should work again
        assert limiter.try_acquire("key1") is True
        assert limiter.try_acquire("key2") is True

    @pytest.mark.asyncio
    async def test_async_acquire(self) -> None:
        """Test async acquire."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        await limiter.acquire()  # Should not block


class TestCreateRateLimiter:
    """Tests for create_rate_limiter function."""

    def test_creates_from_config(self) -> None:
        """Test creating rate limiter from config."""
        config = Config(
            rate_limit_requests_per_minute=120,
            rate_limit_burst=20,
        )
        limiter = create_rate_limiter(config)

        assert limiter.requests_per_minute == 120
        assert limiter.burst_size == 20


class TestRateLimitError:
    """Tests for RateLimitError class."""

    def test_error_message(self) -> None:
        """Test error message formatting."""
        error = RateLimitError("Rate limited", retry_after=5.0)
        assert str(error) == "Rate limited"
        assert error.retry_after == 5.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        error = RateLimitError("Rate limited", retry_after=5.0)
        error_dict = error.to_dict()

        assert error_dict["error"] == "rate_limit_exceeded"
        assert error_dict["retry_after"] == 5.0
