"""MCP server creation and tool registration.

Provides functions for creating FastMCP application instances
and registering core and application-specific tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def create_app(
    config: Config,
    extra_tool_registrars: list[Callable[[Any, Config], None]] | None = None,
) -> FastMCP:
    """Create and configure a FastMCP application instance.

    This is the main entry point for creating an MCP server.
    It registers core tools and any application-specific tools.

    Args:
        config: Application configuration
        extra_tool_registrars: Optional list of additional tool
            registration functions

    Returns:
        Configured FastMCP instance
    """
    # Create FastMCP instance
    app = FastMCP(config.app_name)

    logger.info(
        "Creating MCP server '%s' (environment: %s)",
        config.app_name,
        config.environment.value,
    )

    # Register core tools
    register_core_tools(app, config)

    # Register application-specific tools
    from kepler_mcp_gitlab.application import register_application_tools

    register_application_tools(app, config)

    # Register any extra tool registrars
    if extra_tool_registrars:
        for registrar in extra_tool_registrars:
            registrar(app, config)

    logger.debug("MCP server created with all tools registered")

    return app


def register_core_tools(app: FastMCP, config: Config) -> None:
    """Register core tools that don't depend on external services.

    Core tools include health checks and server information.
    These are always available regardless of configuration.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """
    from kepler_mcp_gitlab.tools.health import register_health_tools
    from kepler_mcp_gitlab.tools.info import register_info_tools

    register_health_tools(app, config)
    register_info_tools(app, config)

    logger.debug("Core tools registered")
