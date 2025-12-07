"""Tests for server module."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from kepler_mcp_gitlab.server import create_app, register_core_tools

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kepler_mcp_gitlab.config import Config


def get_tool_names_sync(app: FastMCP) -> set[str]:
    """Synchronously get tool names from FastMCP app."""
    tools = asyncio.run(app.get_tools())
    return set(tools.keys())


class TestCreateApp:
    """Tests for create_app function."""

    def test_creates_fastmcp_instance(self, default_config: Config) -> None:
        """Test that create_app returns a FastMCP instance."""
        app = create_app(default_config)
        assert app is not None
        # FastMCP should have the app name
        assert app.name == default_config.app_name

    def test_registers_core_tools(self, default_config: Config) -> None:
        """Test that core tools are registered."""
        app = create_app(default_config)

        # Check that health and info tools are registered
        tool_names = get_tool_names_sync(app)
        assert "ping" in tool_names
        assert "health_status" in tool_names
        assert "server_info" in tool_names

    def test_registers_application_tools(self, default_config: Config) -> None:
        """Test that GitLab tools are registered."""
        app = create_app(default_config)

        # Check that GitLab tools from application.py are registered
        tool_names = get_tool_names_sync(app)
        # Project tools
        assert "list_projects" in tool_names
        assert "get_project" in tool_names
        # Issue tools
        assert "list_issues" in tool_names
        assert "create_issue" in tool_names
        # Merge request tools
        assert "list_merge_requests" in tool_names
        assert "create_merge_request" in tool_names
        # Utility tools
        assert "get_current_user" in tool_names
        assert "get_gitlab_config" in tool_names

    def test_extra_registrars_called(self, default_config: Config) -> None:
        """Test that extra tool registrars are called."""
        called = []

        def extra_registrar(app: FastMCP, config: Config) -> None:
            called.append(True)

            @app.tool()  # type: ignore[untyped-decorator]
            def extra_tool() -> str:
                return "extra"

        app = create_app(default_config, extra_tool_registrars=[extra_registrar])

        assert len(called) == 1
        tool_names = get_tool_names_sync(app)
        assert "extra_tool" in tool_names


class TestRegisterCoreTools:
    """Tests for register_core_tools function."""

    def test_registers_health_tools(self, default_config: Config) -> None:
        """Test that health tools are registered."""
        from fastmcp import FastMCP

        app = FastMCP("test")
        register_core_tools(app, default_config)

        tool_names = get_tool_names_sync(app)
        assert "ping" in tool_names
        assert "health_status" in tool_names

    def test_registers_info_tools(self, default_config: Config) -> None:
        """Test that info tools are registered."""
        from fastmcp import FastMCP

        app = FastMCP("test")
        register_core_tools(app, default_config)

        tool_names = get_tool_names_sync(app)
        assert "server_info" in tool_names
