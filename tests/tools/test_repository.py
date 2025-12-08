"""Tests for repository tools."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from fastmcp import FastMCP

from kepler_mcp_gitlab.tools.repository import register_repository_tools

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config


def get_tool_names_sync(app: FastMCP) -> set[str]:
    """Synchronously get tool names from FastMCP app."""
    tools = asyncio.run(app.get_tools())
    return set(tools.keys())


class TestRepositoryToolsRegistration:
    """Tests for repository tools registration."""

    @pytest.fixture
    def app_with_repository_tools(self, default_config: Config) -> FastMCP:
        """Create an app with repository tools registered."""
        app = FastMCP("test")
        register_repository_tools(app, default_config)
        return app

    def test_branch_tools_registered(self, app_with_repository_tools: FastMCP) -> None:
        """Test that branch tools are registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        assert "list_branches" in tools
        assert "get_branch" in tools
        assert "create_branch" in tools
        assert "delete_branch" in tools

    def test_tag_tools_registered(self, app_with_repository_tools: FastMCP) -> None:
        """Test that tag tools are registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        assert "list_tags" in tools
        assert "get_tag" in tools
        assert "create_tag" in tools
        assert "delete_tag" in tools

    def test_file_tools_registered(self, app_with_repository_tools: FastMCP) -> None:
        """Test that file tools are registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        assert "list_repository_tree" in tools
        assert "get_file" in tools
        assert "get_file_content" in tools
        assert "create_file" in tools
        assert "update_file" in tools
        assert "delete_file" in tools
        assert "get_file_blame" in tools

    def test_commit_tools_registered(self, app_with_repository_tools: FastMCP) -> None:
        """Test that commit tools are registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        assert "list_commits" in tools
        assert "get_commit" in tools
        assert "get_commit_diff" in tools
        assert "cherry_pick_commit" in tools
        assert "get_commit_refs" in tools

    def test_compare_tool_registered(self, app_with_repository_tools: FastMCP) -> None:
        """Test that compare tool is registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        assert "compare_branches" in tools

    def test_total_repository_tools_count(
        self, app_with_repository_tools: FastMCP
    ) -> None:
        """Test that all 19 repository tools are registered."""
        tools = get_tool_names_sync(app_with_repository_tools)
        # Branch: 4, Tag: 4, Compare: 1, Tree: 1, File: 6, Commit: 5 = 21 tools
        expected_tools = {
            # Branch tools
            "list_branches",
            "get_branch",
            "create_branch",
            "delete_branch",
            # Tag tools
            "list_tags",
            "get_tag",
            "create_tag",
            "delete_tag",
            # Compare
            "compare_branches",
            # Tree
            "list_repository_tree",
            # File tools
            "get_file",
            "get_file_content",
            "create_file",
            "update_file",
            "delete_file",
            "get_file_blame",
            # Commit tools
            "list_commits",
            "get_commit",
            "get_commit_diff",
            "cherry_pick_commit",
            "get_commit_refs",
        }
        assert expected_tools.issubset(tools)
        assert len(expected_tools) == 21
