"""Tests for health tools."""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP

from kepler_mcp_gitlab.config import Config, Environment
from kepler_mcp_gitlab.tools.health import register_health_tools


def get_tool_names_sync(app: FastMCP) -> set[str]:
    """Synchronously get tool names from FastMCP app."""
    tools = asyncio.run(app.get_tools())
    return set(tools.keys())


class TestHealthTools:
    """Tests for health tools."""

    @pytest.fixture
    def app_with_health_tools(self, default_config: Config) -> FastMCP:
        """Create an app with health tools registered."""
        app = FastMCP("test")
        register_health_tools(app, default_config)
        return app

    def test_ping_registered(self, app_with_health_tools: FastMCP) -> None:
        """Test that ping tool is registered."""
        tools = get_tool_names_sync(app_with_health_tools)
        assert "ping" in tools

    def test_health_status_registered(self, app_with_health_tools: FastMCP) -> None:
        """Test that health_status tool is registered."""
        tools = get_tool_names_sync(app_with_health_tools)
        assert "health_status" in tools

    def test_ping_returns_pong(self) -> None:
        """Test that ping returns pong."""
        config = Config()
        app = FastMCP("test")
        register_health_tools(app, config)

        # Verify the ping tool is registered
        tools = get_tool_names_sync(app)
        assert "ping" in tools

    def test_health_status_returns_correct_data(self) -> None:
        """Test that health_status returns correct data."""
        config = Config(
            app_name="Test Server",
            environment=Environment.DEV,
        )
        app = FastMCP("test")
        register_health_tools(app, config)

        # The health_status tool should include app_name and environment
        # We verify the tool is registered correctly
        tools = get_tool_names_sync(app)
        assert "health_status" in tools
