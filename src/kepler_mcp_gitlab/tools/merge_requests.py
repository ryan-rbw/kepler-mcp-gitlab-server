"""GitLab merge request tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.context import get_gitlab_client_for_context
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_merge_request_tools(app: Any, config: Config) -> None:
    """Register GitLab merge request tools.

    Args:
        app: FastMCP application instance
        config: Application configuration
    """

    @app.tool()
    async def list_merge_requests(
        ctx: Context,
        project_id: str,
        state: str | None = None,
        labels: str | None = None,
        milestone: str | None = None,
        scope: str | None = None,
        author_id: int | None = None,
        assignee_id: int | None = None,
        reviewer_id: int | None = None,
        source_branch: str | None = None,
        target_branch: str | None = None,
        search: str | None = None,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List merge requests in a GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            state: Filter by state (opened, closed, merged, all)
            labels: Comma-separated list of label names
            milestone: Filter by milestone title
            scope: Filter by scope (created_by_me, assigned_to_me, all)
            author_id: Filter by author user ID
            assignee_id: Filter by assignee user ID
            reviewer_id: Filter by reviewer user ID
            source_branch: Filter by source branch name
            target_branch: Filter by target branch name
            search: Search in title and description
            order_by: Order by field (created_at, updated_at)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of merge request objects with id, iid, title, state, source_branch, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        merge_requests = await client.list_merge_requests(
            project_id=project_id,
            state=state,
            labels=labels,
            milestone=milestone,
            scope=scope,
            author_id=author_id,
            assignee_id=assignee_id,
            reviewer_id=reviewer_id,
            source_branch=source_branch,
            target_branch=target_branch,
            search=search,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return merge_requests[:max_items]

    @app.tool()
    async def get_merge_request(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        include_diverged_commits_count: bool = False,
        include_rebase_in_progress: bool = False,
    ) -> dict[str, Any]:
        """Get details of a specific merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number in GitLab UI)
            include_diverged_commits_count: Include count of diverged commits
            include_rebase_in_progress: Include rebase in progress status

        Returns:
            Merge request object with full details including title, description,
            state, source_branch, target_branch, author, assignees, reviewers,
            pipeline status, merge status, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_merge_request(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            include_diverged_commits_count=include_diverged_commits_count,
            include_rebase_in_progress=include_rebase_in_progress,
        )

    @app.tool()
    async def create_merge_request(
        ctx: Context,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str | None = None,
        assignee_ids: list[int] | None = None,
        reviewer_ids: list[int] | None = None,
        labels: str | None = None,
        milestone_id: int | None = None,
        remove_source_branch: bool = False,
        squash: bool = False,
        draft: bool = False,
    ) -> dict[str, Any]:
        """Create a new merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            source_branch: Source branch name (the branch with changes)
            target_branch: Target branch name (the branch to merge into)
            title: Merge request title
            description: Merge request description (Markdown supported)
            assignee_ids: List of user IDs to assign
            reviewer_ids: List of user IDs to request review
            labels: Comma-separated list of label names
            milestone_id: Milestone ID to associate
            remove_source_branch: Delete source branch after merge
            squash: Squash commits on merge
            draft: Create as draft/WIP merge request

        Returns:
            Created merge request object with id, iid, web_url, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_merge_request(
            project_id=project_id,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            description=description,
            assignee_ids=assignee_ids,
            reviewer_ids=reviewer_ids,
            labels=labels,
            milestone_id=milestone_id,
            remove_source_branch=remove_source_branch,
            squash=squash,
            draft=draft,
        )

    @app.tool()
    async def update_merge_request(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        title: str | None = None,
        description: str | None = None,
        state_event: str | None = None,
        target_branch: str | None = None,
        assignee_ids: list[int] | None = None,
        reviewer_ids: list[int] | None = None,
        labels: str | None = None,
        milestone_id: int | None = None,
        remove_source_branch: bool | None = None,
        squash: bool | None = None,
    ) -> dict[str, Any]:
        """Update an existing merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            title: New title
            description: New description (Markdown supported)
            state_event: State change action (close, reopen)
            target_branch: New target branch
            assignee_ids: List of user IDs to assign (replaces existing)
            reviewer_ids: List of user IDs to request review (replaces existing)
            labels: Comma-separated list of label names (replaces existing)
            milestone_id: Milestone ID (use 0 to unset)
            remove_source_branch: Delete source branch after merge
            squash: Squash commits on merge

        Returns:
            Updated merge request object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.update_merge_request(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            title=title,
            description=description,
            state_event=state_event,
            target_branch=target_branch,
            assignee_ids=assignee_ids,
            reviewer_ids=reviewer_ids,
            labels=labels,
            milestone_id=milestone_id,
            remove_source_branch=remove_source_branch,
            squash=squash,
        )

    @app.tool()
    async def merge_merge_request(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        merge_commit_message: str | None = None,
        squash_commit_message: str | None = None,
        squash: bool = False,
        should_remove_source_branch: bool = False,
        merge_when_pipeline_succeeds: bool = False,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Merge a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            merge_commit_message: Custom merge commit message
            squash_commit_message: Custom squash commit message
            squash: Squash commits before merging
            should_remove_source_branch: Delete source branch after merge
            merge_when_pipeline_succeeds: Auto-merge when pipeline passes
            sha: Expected HEAD SHA of source branch (for safety check)

        Returns:
            Merged merge request object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.merge_merge_request(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            merge_commit_message=merge_commit_message,
            squash_commit_message=squash_commit_message,
            squash=squash,
            should_remove_source_branch=should_remove_source_branch,
            merge_when_pipeline_succeeds=merge_when_pipeline_succeeds,
            sha=sha,
        )

    @app.tool()
    async def approve_merge_request(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Approve a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            sha: Expected HEAD SHA of source branch (for safety check)

        Returns:
            Approval result object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.approve_merge_request(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            sha=sha,
        )

    @app.tool()
    async def unapprove_merge_request(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
    ) -> dict[str, Any]:
        """Remove your approval from a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)

        Returns:
            Unapproval result object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.unapprove_merge_request(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
        )

    @app.tool()
    async def get_merge_request_changes(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
    ) -> dict[str, Any]:
        """Get the file changes (diff) of a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)

        Returns:
            Merge request object including 'changes' array with file diffs.
            Each change includes old_path, new_path, diff content, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_merge_request_changes(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
        )

    @app.tool()
    async def list_merge_request_comments(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        order_by: str = "created_at",
        sort: str = "asc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List comments (notes) on a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            order_by: Order by field (created_at, updated_at)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of note objects with id, body, author, created_at, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        notes = await client.list_merge_request_notes(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return notes[:max_items]

    @app.tool()
    async def add_merge_request_comment(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        body: str,
    ) -> dict[str, Any]:
        """Add a comment (note) to a merge request.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            body: Comment body (Markdown supported)

        Returns:
            Created note object with id, body, author, created_at, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_merge_request_note(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            body=body,
        )

    @app.tool()
    async def list_merge_request_discussions(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List discussion threads on a merge request.

        Discussion threads include code review comments on specific lines.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of discussion objects, each containing notes array with
            the thread's comments.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        discussions = await client.list_merge_request_discussions(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            per_page=per_page,
            max_pages=max_pages,
        )
        return discussions[:max_items]

    @app.tool()
    async def resolve_merge_request_discussion(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
        discussion_id: str,
        resolved: bool = True,
    ) -> dict[str, Any]:
        """Resolve or unresolve a merge request discussion thread.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)
            discussion_id: Discussion thread ID
            resolved: True to resolve, False to unresolve

        Returns:
            Updated discussion object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.resolve_merge_request_discussion(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            discussion_id=discussion_id,
            resolved=resolved,
        )

    @app.tool()
    async def get_merge_request_participants(
        ctx: Context,
        project_id: str,
        merge_request_iid: int,
    ) -> list[dict[str, Any]]:
        """Get users who participated in a merge request.

        Participants include the author, assignees, reviewers, and commenters.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            merge_request_iid: Merge request internal ID (the ! number)

        Returns:
            List of user objects with id, username, name, avatar_url, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_merge_request_participants(
            project_id=project_id,
            merge_request_iid=merge_request_iid,
        )

    logger.debug("Merge request tools registered")
