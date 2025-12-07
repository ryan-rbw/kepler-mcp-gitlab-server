"""GitLab issue tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.context import get_gitlab_client_for_context
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_issue_tools(app: Any, config: Config) -> None:
    """Register GitLab issue tools.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()
    async def list_issues(
        ctx: Context,
        project_id: str,
        state: str | None = None,
        labels: str | None = None,
        milestone: str | None = None,
        assignee_id: int | None = None,
        author_id: int | None = None,
        search: str | None = None,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List issues in a GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            state: Filter by state (opened, closed, all)
            labels: Comma-separated list of label names to filter by
            milestone: Filter by milestone title
            assignee_id: Filter by assignee user ID
            author_id: Filter by author user ID
            search: Search in title and description
            order_by: Order by field (created_at, updated_at, priority, etc.)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of issue objects with id, iid, title, description, state, labels, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        issues = await client.list_issues(
            project_id=project_id,
            state=state,
            labels=labels,
            milestone=milestone,
            assignee_id=assignee_id,
            author_id=author_id,
            search=search,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return issues[:max_items]

    @app.tool()
    async def get_issue(
        ctx: Context,
        project_id: str,
        issue_iid: int,
    ) -> dict[str, Any]:
        """Get details of a specific issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)

        Returns:
            Issue object with full details including title, description, state,
            labels, assignees, milestone, due_date, time_stats, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_issue(project_id, issue_iid)

    @app.tool()
    async def create_issue(
        ctx: Context,
        project_id: str,
        title: str,
        description: str | None = None,
        labels: str | None = None,
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
        confidential: bool = False,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue in a GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            title: Issue title (required)
            description: Issue description (Markdown supported)
            labels: Comma-separated list of label names
            assignee_ids: List of user IDs to assign
            milestone_id: Milestone ID to associate
            confidential: Whether the issue is confidential
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Created issue object with id, iid, web_url, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_issue(
            project_id=project_id,
            title=title,
            description=description,
            labels=labels,
            assignee_ids=assignee_ids,
            milestone_id=milestone_id,
            confidential=confidential,
            due_date=due_date,
        )

    @app.tool()
    async def update_issue(
        ctx: Context,
        project_id: str,
        issue_iid: int,
        title: str | None = None,
        description: str | None = None,
        state_event: str | None = None,
        labels: str | None = None,
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
        confidential: bool | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)
            title: New title
            description: New description (Markdown supported)
            state_event: State change action (close, reopen)
            labels: Comma-separated list of label names (replaces existing labels)
            assignee_ids: List of user IDs to assign (replaces existing assignees)
            milestone_id: Milestone ID (use 0 to unset)
            confidential: Whether the issue is confidential
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Updated issue object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.update_issue(
            project_id=project_id,
            issue_iid=issue_iid,
            title=title,
            description=description,
            state_event=state_event,
            labels=labels,
            assignee_ids=assignee_ids,
            milestone_id=milestone_id,
            confidential=confidential,
            due_date=due_date,
        )

    @app.tool()
    async def close_issue(
        ctx: Context,
        project_id: str,
        issue_iid: int,
    ) -> dict[str, Any]:
        """Close an issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)

        Returns:
            Updated issue object with state "closed"
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.update_issue(
            project_id=project_id,
            issue_iid=issue_iid,
            state_event="close",
        )

    @app.tool()
    async def reopen_issue(
        ctx: Context,
        project_id: str,
        issue_iid: int,
    ) -> dict[str, Any]:
        """Reopen a closed issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)

        Returns:
            Updated issue object with state "opened"
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.update_issue(
            project_id=project_id,
            issue_iid=issue_iid,
            state_event="reopen",
        )

    @app.tool()
    async def list_issue_comments(
        ctx: Context,
        project_id: str,
        issue_iid: int,
        order_by: str = "created_at",
        sort: str = "asc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List comments (notes) on an issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)
            order_by: Order by field (created_at, updated_at)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of note objects with id, body, author, created_at, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        notes = await client.list_issue_notes(
            project_id=project_id,
            issue_iid=issue_iid,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return notes[:max_items]

    @app.tool()
    async def add_issue_comment(
        ctx: Context,
        project_id: str,
        issue_iid: int,
        body: str,
        confidential: bool = False,
    ) -> dict[str, Any]:
        """Add a comment (note) to an issue.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            issue_iid: Issue internal ID (the # number shown in GitLab UI)
            body: Comment body (Markdown supported)
            confidential: Whether the comment is confidential (visible only to project members)

        Returns:
            Created note object with id, body, author, created_at, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_issue_note(
            project_id=project_id,
            issue_iid=issue_iid,
            body=body,
            confidential=confidential,
        )

    logger.debug("Issue tools registered")
