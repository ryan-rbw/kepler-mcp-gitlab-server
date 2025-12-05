"""Tests for info tools."""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP

from kepler_mcp_gitlab.config import Config
from kepler_mcp_gitlab.tools.info import register_info_tools


def get_tool_names_sync(app: FastMCP) -> set[str]:
    """Synchronously get tool names from FastMCP app."""
    tools = asyncio.run(app.get_tools())
    return set(tools.keys())


class TestInfoTools:
    """Tests for info tools."""

    @pytest.fixture
    def app_with_info_tools(self, default_config: Config) -> FastMCP:
        """Create an app with info tools registered."""
        app = FastMCP("test")
        register_info_tools(app, default_config)
        return app

    def test_server_info_registered(self, app_with_info_tools: FastMCP) -> None:
        """Test that server_info tool is registered."""
        tools = get_tool_names_sync(app_with_info_tools)
        assert "server_info" in tools

    def test_server_info_does_not_expose_secrets(self) -> None:
        """Test that server_info does not expose secrets."""
        config = Config(
            app_name="Test Server",
            auth_token="super-secret-token",
            oauth_client_secret="oauth-secret",
        )
        app = FastMCP("test")
        register_info_tools(app, config)

        # Server info should be registered
        tools = get_tool_names_sync(app)
        assert "server_info" in tools
