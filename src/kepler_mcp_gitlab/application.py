"""Application-specific tool registration hook.

This module provides the extension point for registering
GitLab-specific tools for the MCP server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.context import (
    get_gitlab_client_for_context,
    get_session_manager,
    set_session_manager,
)
from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.tools.issues import register_issue_tools
from kepler_mcp_gitlab.tools.merge_requests import register_merge_request_tools
from kepler_mcp_gitlab.tools.projects import register_project_tools
from kepler_mcp_gitlab.tools.repository import register_repository_tools

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)

# Re-export for backwards compatibility
__all__ = [
    "get_gitlab_client_for_context",
    "get_session_manager",
    "register_application_tools",
    "set_session_manager",
]


def register_application_tools(app: Any, config: Config) -> None:
    """Register GitLab tools on the FastMCP app.

    This function registers all GitLab API tools including:
    - Project tools (list, get, search projects)
    - Issue tools (list, create, update, comment on issues)
    - Merge Request tools (list, create, merge, approve MRs)
    - Repository tools (branches, tags, files, commits)

    Args:
        app: FastMCP application instance
        config: Application configuration with GitLab settings
    """
    # Register all tool modules
    # Tools will use get_gitlab_client_for_context() to get authenticated clients
    register_project_tools(app, config)
    register_issue_tools(app, config)
    register_merge_request_tools(app, config)
    register_repository_tools(app, config)

    # Register utility tools
    _register_utility_tools(app, config)

    logger.info(
        "GitLab tools registered for %s",
        config.gitlab_url,
    )


def _register_utility_tools(app: Any, config: Config) -> None:
    """Register utility tools for debugging and info.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """
    _session_manager = get_session_manager()

    @app.tool()
    async def get_current_user(ctx: Context) -> dict[str, Any]:
        """Get information about the currently authenticated GitLab user.

        Returns:
            User object with id, username, name, email, avatar_url,
            web_url, and other profile information.
        """
        try:
            client = await get_gitlab_client_for_context(ctx, config)
            return await client.get_current_user()
        except Exception as e:
            return {"error": str(e)}

    @app.tool()
    def get_gitlab_config() -> dict[str, str]:
        """Get the current GitLab configuration (non-sensitive info only).

        Returns:
            Dictionary with gitlab_url and auth_method
        """
        auth_method = "oauth" if _session_manager is not None else "none"
        return {
            "gitlab_url": config.gitlab_url,
            "auth_method": auth_method,
        }

    logger.debug("Utility tools registered")
