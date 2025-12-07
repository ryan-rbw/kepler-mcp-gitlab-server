"""GitLab project tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.context import get_gitlab_client_for_context
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_project_tools(app: Any, config: Config) -> None:
    """Register GitLab project tools.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()
    async def list_projects(
        ctx: Context,
        search: str | None = None,
        visibility: str | None = None,
        owned: bool = False,
        membership: bool = False,
        archived: bool | None = None,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List GitLab projects accessible to the authenticated user.

        Args:
            ctx: Request context (injected automatically)
            search: Search term for project name, path, or description
            visibility: Filter by visibility (public, internal, private)
            owned: Only return projects owned by the user
            membership: Only return projects where user is a member
            archived: Filter by archived status (true/false/None for all)
            order_by: Order by field (id, name, path, created_at, updated_at, last_activity_at)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of project objects with id, name, path, description, visibility, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        projects = await client.list_projects(
            search=search,
            visibility=visibility,
            owned=owned,
            membership=membership,
            archived=archived,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return projects[:max_items]

    @app.tool()
    async def get_project(
        ctx: Context,
        project_id: str,
        statistics: bool = False,
    ) -> dict[str, Any]:
        """Get details of a specific GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            statistics: Include project statistics (commit count, storage, etc.)

        Returns:
            Project object with full details including id, name, path, description,
            visibility, default_branch, web_url, and more.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_project(project_id, statistics=statistics)

    @app.tool()
    async def search_projects(
        ctx: Context,
        query: str,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """Search for GitLab projects by name, path, or description.

        Args:
            ctx: Request context (injected automatically)
            query: Search query string
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of matching project objects
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        projects = await client.list_projects(
            search=query,
            per_page=per_page,
            max_pages=max_pages,
        )
        return projects[:max_items]

    @app.tool()
    async def get_project_languages(
        ctx: Context,
        project_id: str,
    ) -> dict[str, float]:
        """Get programming languages used in a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")

        Returns:
            Dictionary mapping language names to percentage usage.
            Example: {"Python": 75.5, "JavaScript": 20.3, "Shell": 4.2}
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_project_languages(project_id)

    logger.debug("Project tools registered")
