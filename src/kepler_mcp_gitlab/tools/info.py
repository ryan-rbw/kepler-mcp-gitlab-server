"""Server information MCP tools.

Provides introspection tools for server metadata.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from kepler_mcp_gitlab import __version__
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_info_tools(app: Any, config: Config) -> None:
    """Register information tools on the FastMCP app.

    Info tools provide server metadata and version information.
    They do not reveal sensitive configuration.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()  # type: ignore[untyped-decorator]
    def server_info() -> dict[str, str]:
        """Get server version and metadata.

        Returns non-sensitive server information including
        application name, package version, FastMCP version,
        and Python version.

        Returns:
            Dictionary with server information
        """
        # Get FastMCP version
        fastmcp_version = "unknown"
        try:
            import fastmcp

            fastmcp_version = getattr(fastmcp, "__version__", "unknown")
        except ImportError:
            pass

        vi = sys.version_info
        return {
            "app_name": config.app_name,
            "version": __version__,
            "fastmcp_version": fastmcp_version,
            "python_version": f"{vi.major}.{vi.minor}.{vi.micro}",
        }

    logger.debug("Info tools registered (server_info)")
