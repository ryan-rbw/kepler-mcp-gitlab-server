"""Application-specific tool registration hook.

This module provides the extension point for registering
application-specific tools. When creating a specific MCP server
(e.g., GitLab, JIRA), modify this file to register the
appropriate tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_application_tools(app: Any, config: Config) -> None:
    """Register application-specific tools on the FastMCP app.

    This function is the main extension point for application-specific
    integrations. When building a server for a specific service
    (e.g., GitLab, JIRA, Confluence), implement the tool registration
    logic here.

    IMPORTANT: This function should not perform blocking network I/O.
    API clients and auth strategies can be constructed here, but
    all external calls must happen inside the tool functions.

    Args:
        app: FastMCP application instance
        config: Application configuration (may include custom fields)

    Example:
        For a GitLab integration:

        ```python
        def register_application_tools(app: Any, config: Config) -> None:
            from myapp.gitlab_tools import (
                list_projects,
                get_merge_requests,
                create_issue,
            )

            # Register tools
            app.tool(list_projects)
            app.tool(get_merge_requests)
            app.tool(create_issue)
        ```
    """
    # Register example echo tool for template demonstration
    _register_example_tools(app, config)

    logger.debug("Application tools registered")


def _register_example_tools(app: Any, config: Config) -> None:
    """Register example tools for template demonstration.

    These tools serve as examples and can be removed when
    implementing a real integration.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()  # type: ignore[untyped-decorator]
    def echo(message: str) -> str:
        """Echo a message back to the client.

        A simple example tool that demonstrates the tool interface.

        Args:
            message: The message to echo

        Returns:
            The same message prefixed with application name
        """
        return f"[{config.app_name}] {message}"

    @app.tool()  # type: ignore[untyped-decorator]
    def get_config_info() -> dict[str, str]:
        """Get non-sensitive configuration information.

        Returns basic server configuration for debugging purposes.
        Does not expose any secrets or sensitive values.

        Returns:
            Dictionary with configuration details
        """
        return {
            "app_name": config.app_name,
            "environment": config.environment.value,
            "transport_mode": config.transport_mode.value,
            "oauth_user_auth_enabled": str(config.oauth_user_auth_enabled),
            "oauth_service_auth_enabled": str(config.oauth_service_auth_enabled),
        }

    logger.debug("Example tools registered (echo, get_config_info)")
