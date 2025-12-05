"""Rate limiting utilities for Kepler MCP Server.

Implements token bucket algorithm for rate limiting outbound API calls.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Implements the token bucket algorithm where tokens are added
    at a fixed rate and consumed by requests.
    """

    capacity: float
    tokens: float
    fill_rate: float  # tokens per second
    last_update: float = field(default_factory=time.monotonic)

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        self.last_update = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: float = 1.0) -> float:
        """Calculate time until requested tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens are available (0 if already available)
        """
        self.refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.fill_rate


class RateLimiter:
    """Rate limiter using token bucket algorithm.

    Supports per-key rate limiting for user/session isolation.

    Example:
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)

        # Blocking acquire
        await limiter.acquire("user123")

        # Non-blocking check
        if limiter.try_acquire("user123"):
            # Proceed with request
            ...
        else:
            # Handle rate limit
            retry_after = limiter.get_retry_after("user123")
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ) -> None:
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum sustained request rate
            burst_size: Maximum burst capacity
        """
        self._requests_per_minute = requests_per_minute
        self._burst_size = burst_size
        self._fill_rate = requests_per_minute / 60.0  # tokens per second
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create a token bucket for a key.

        Args:
            key: Rate limit key (e.g., user ID, session ID)

        Returns:
            TokenBucket for the key
        """
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=float(self._burst_size),
                tokens=float(self._burst_size),
                fill_rate=self._fill_rate,
            )
        return self._buckets[key]

    async def acquire(self, key: str = "default") -> None:
        """Acquire permission to make a request, blocking if necessary.

        Waits until a token is available in the bucket.

        Args:
            key: Rate limit key for per-user/session limiting
        """
        async with self._lock:
            bucket = self._get_bucket(key)

            while not bucket.consume():
                wait_time = bucket.time_until_available()
                logger.debug(
                    "Rate limit reached for key '%s', waiting %.2f seconds",
                    key,
                    wait_time,
                )
                # Release lock while waiting
                self._lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    await self._lock.acquire()
                bucket = self._get_bucket(key)

    def try_acquire(self, key: str = "default") -> bool:
        """Non-blocking attempt to acquire permission.

        Args:
            key: Rate limit key for per-user/session limiting

        Returns:
            True if request is allowed, False if rate limited
        """
        bucket = self._get_bucket(key)
        return bucket.consume()

    def get_retry_after(self, key: str = "default") -> float:
        """Get seconds until next request is allowed.

        Args:
            key: Rate limit key

        Returns:
            Seconds until a token is available
        """
        bucket = self._get_bucket(key)
        return bucket.time_until_available()

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit state.

        Args:
            key: Specific key to reset, or None to reset all
        """
        if key is None:
            self._buckets.clear()
        elif key in self._buckets:
            del self._buckets[key]

    @property
    def requests_per_minute(self) -> int:
        """Get configured requests per minute limit."""
        return self._requests_per_minute

    @property
    def burst_size(self) -> int:
        """Get configured burst size."""
        return self._burst_size


def create_rate_limiter(config: Config) -> RateLimiter:
    """Create a rate limiter from configuration.

    Args:
        config: Application configuration

    Returns:
        Configured RateLimiter instance
    """
    return RateLimiter(
        requests_per_minute=config.rate_limit_requests_per_minute,
        burst_size=config.rate_limit_burst,
    )


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds until retry is allowed
        """
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, str | float]:
        """Convert to dictionary for API response.

        Returns:
            Dictionary with error details
        """
        return {
            "error": "rate_limit_exceeded",
            "message": str(self),
            "retry_after": self.retry_after,
        }
