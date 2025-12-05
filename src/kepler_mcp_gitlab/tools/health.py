"""Health-related MCP tools.

Provides basic health check tools that don't depend on external services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_health_tools(app: Any, config: Config) -> None:
    """Register health-related tools on the FastMCP app.

    Health tools provide basic availability checks and should
    always be responsive as long as the server is running.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()  # type: ignore[untyped-decorator]
    def ping() -> str:
        """Simple ping/pong health check.

        Returns a constant "pong" string to verify the server
        is responsive.

        Returns:
            The string "pong"
        """
        return "pong"

    @app.tool()  # type: ignore[untyped-decorator]
    def health_status() -> dict[str, str]:
        """Get server health status.

        Returns basic health information including server status,
        application name, and environment.

        Returns:
            Dictionary with health status details
        """
        return {
            "status": "ok",
            "app_name": config.app_name,
            "environment": config.environment.value,
        }

    logger.debug("Health tools registered (ping, health_status)")
