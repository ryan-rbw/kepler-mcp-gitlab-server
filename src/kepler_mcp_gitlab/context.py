"""Context utilities for GitLab MCP tools.

Provides functions to get authenticated GitLab clients from request context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.gitlab.client import (
    GitLabClient,
    GitLabNoAuthStrategy,
    GitLabOAuthAuthStrategy,
)
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config
    from kepler_mcp_gitlab.oauth.session import SessionManager
    from kepler_mcp_gitlab.security import AuthStrategy

logger = get_logger(__name__)

# Global session manager reference (set during SSE setup)
_session_manager: SessionManager | None = None

# Mapping from MCP transport session IDs to OAuth session IDs
# This allows tools to get the OAuth session from the MCP context
_transport_to_oauth_session: dict[str, str] = {}


def set_session_manager(session_manager: SessionManager) -> None:
    """Set the global session manager for OAuth authentication.

    This should be called during SSE transport setup before tools are used.

    Args:
        session_manager: SessionManager instance with token store
    """
    global _session_manager  # noqa: PLW0603
    _session_manager = session_manager
    logger.debug("Session manager configured for OAuth authentication")


def get_session_manager() -> SessionManager | None:
    """Get the global session manager.

    Returns:
        SessionManager if configured, None otherwise
    """
    return _session_manager


def register_transport_session(transport_session_id: str, oauth_session_id: str) -> None:
    """Register a mapping from MCP transport session to OAuth session.

    Called when an SSE connection is established to link the MCP transport
    session with the user's OAuth session from the cookie.

    Args:
        transport_session_id: The MCP transport session ID
        oauth_session_id: The OAuth session ID from the cookie
    """
    _transport_to_oauth_session[transport_session_id] = oauth_session_id
    logger.debug(
        "Registered transport session %s -> OAuth session %s",
        transport_session_id[:8],
        oauth_session_id[:8],
    )


def unregister_transport_session(transport_session_id: str) -> None:
    """Remove a transport session mapping.

    Called when an SSE connection is closed.

    Args:
        transport_session_id: The MCP transport session ID to remove
    """
    if transport_session_id in _transport_to_oauth_session:
        del _transport_to_oauth_session[transport_session_id]
        logger.debug("Unregistered transport session %s", transport_session_id[:8])


def get_oauth_session_for_transport(transport_session_id: str) -> str | None:
    """Get the OAuth session ID for an MCP transport session.

    Args:
        transport_session_id: The MCP transport session ID

    Returns:
        OAuth session ID if found, None otherwise
    """
    return _transport_to_oauth_session.get(transport_session_id)


async def get_gitlab_client_for_context(
    ctx: Context,
    config: Config,
) -> GitLabClient:
    """Get a GitLab client authenticated for the current request context.

    In SSE mode with OAuth, this extracts the session from the request
    and creates a client with the user's OAuth tokens.

    In stdio mode or without OAuth, returns an unauthenticated client.

    Args:
        ctx: FastMCP context with request information
        config: Application configuration

    Returns:
        GitLabClient configured with appropriate authentication

    Raises:
        ValueError: If OAuth is enabled but session is invalid
    """
    auth_strategy: AuthStrategy
    oauth_session_id: str | None = None

    # Check if we have a session manager (SSE mode with OAuth)
    if _session_manager is not None:
        # First, try to get OAuth session from transport session mapping
        # This is set when the SSE connection is established
        transport_session_id = ctx.session_id
        if transport_session_id:
            oauth_session_id = get_oauth_session_for_transport(transport_session_id)
            if oauth_session_id:
                logger.debug(
                    "Found OAuth session %s for transport %s",
                    oauth_session_id[:8],
                    transport_session_id[:8],
                )

        # Fallback: try to get from HTTP request cookies
        if not oauth_session_id:
            try:
                request = ctx.get_http_request()
                oauth_session_id = request.cookies.get("session_id")
                if oauth_session_id:
                    logger.debug(
                        "Got OAuth session %s from cookie", oauth_session_id[:8]
                    )
            except Exception as e:
                logger.debug("Could not get HTTP request: %s", e)

        if oauth_session_id:
            auth_strategy = GitLabOAuthAuthStrategy(_session_manager, oauth_session_id)
            logger.debug("Using OAuth authentication for session %s", oauth_session_id[:8])
        else:
            logger.warning("No OAuth session found, using unauthenticated access")
            auth_strategy = GitLabNoAuthStrategy()
    else:
        # No session manager - unauthenticated access only
        auth_strategy = GitLabNoAuthStrategy()

    return GitLabClient(config.gitlab_url, auth_strategy)
