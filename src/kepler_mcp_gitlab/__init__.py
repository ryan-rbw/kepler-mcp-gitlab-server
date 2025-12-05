"""Kepler MCP Server Template.

A production-ready MCP server template with OAuth 2.0, FastMCP, and Docker support.
"""

__version__ = "0.1.0"

from kepler_mcp_gitlab.config import Config, ConfigError, load_config
from kepler_mcp_gitlab.server import create_app, register_core_tools

__all__ = [
    "Config",
    "ConfigError",
    "__version__",
    "create_app",
    "load_config",
    "register_core_tools",
]
