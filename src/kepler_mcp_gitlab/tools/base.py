"""Base utilities for defining MCP tools.

Provides decorators and helper functions for consistent
tool implementation across the application.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.security import mask_sensitive_data

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def kepler_tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for MCP tools with logging and error handling.

    Wraps tool functions with:
    - Debug logging of tool entry and exit
    - Automatic exception handling
    - Sensitive data masking in logs

    Args:
        name: Optional tool name (defaults to function name)
        description: Optional tool description

    Returns:
        Decorated function

    Example:
        @kepler_tool(name="get_user", description="Get user details")
        def get_user(user_id: str) -> dict:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Log entry with masked kwargs
            masked_kwargs = mask_sensitive_data(dict(kwargs))
            logger.debug(
                "Tool %s called with args=%s, kwargs=%s", tool_name, args, masked_kwargs
            )

            try:
                result = func(*args, **kwargs)
                logger.debug("Tool %s completed successfully", tool_name)
                return result
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                raise ToolError(f"Tool {tool_name} failed: {e}") from e

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Log entry with masked kwargs
            masked_kwargs = mask_sensitive_data(dict(kwargs))
            logger.debug(
                "Tool %s called with args=%s, kwargs=%s", tool_name, args, masked_kwargs
            )

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                logger.debug("Tool %s completed successfully", tool_name)
                return result  # type: ignore[no-any-return]
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                raise ToolError(f"Tool {tool_name} failed: {e}") from e

        # Check if function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


class ToolError(Exception):
    """Error raised when a tool execution fails.

    This error is caught by the MCP framework and returned
    to the client as a structured error response.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize tool error.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional additional error details
        """
        super().__init__(message)
        self.error_code = error_code or "TOOL_ERROR"
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response.

        Returns:
            Error as dictionary
        """
        return {
            "error": self.error_code,
            "message": str(self),
            "details": self.details,
        }


class RateLimitedError(ToolError):
    """Error raised when a tool is rate limited."""

    def __init__(self, retry_after: float) -> None:
        """Initialize rate limit error.

        Args:
            retry_after: Seconds until retry is allowed
        """
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after:.1f} seconds",
            error_code="RATE_LIMITED",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after
