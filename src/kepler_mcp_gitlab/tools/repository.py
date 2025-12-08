"""GitLab repository tools for branches, tags, files, and commits."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context  # noqa: TC002 - needed at runtime for FastMCP injection

from kepler_mcp_gitlab.context import get_gitlab_client_for_context
from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

logger = get_logger(__name__)


def register_repository_tools(app: Any, config: Config) -> None:
    """Register repository tools with the MCP application.

    This module registers tools for:
    - Branches: list, get, create, delete
    - Tags: list, get, create, delete
    - Compare: compare branches/tags/commits
    - Tree: list repository files/directories
    - Files: get, create, update, delete, blame
    - Commits: list, get, diff, cherry-pick, refs

    Args:
        app: FastMCP application instance
        config: Application configuration
    """
    _register_branch_tools(app, config)
    _register_tag_tools(app, config)
    _register_compare_tools(app, config)
    _register_tree_tools(app, config)
    _register_file_tools(app, config)
    _register_commit_tools(app, config)

    logger.info("Repository tools registered (branches, tags, files, commits)")


def _register_branch_tools(app: Any, config: Config) -> None:
    """Register branch-related tools."""

    @app.tool()
    async def list_branches(
        ctx: Context,
        project_id: str,
        search: str | None = None,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List branches in a GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            search: Search term for branch names
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of branch objects with name, commit info, protected status, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        branches = await client.list_branches(
            project_id, search=search, per_page=per_page, max_pages=max_pages
        )
        return branches[:max_items]

    @app.tool()
    async def get_branch(
        ctx: Context,
        project_id: str,
        branch_name: str,
    ) -> dict[str, Any]:
        """Get details of a specific branch.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            branch_name: Name of the branch

        Returns:
            Branch object with name, commit info, protected status,
            developers_can_push, developers_can_merge, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_branch(project_id, branch_name)

    @app.tool()
    async def create_branch(
        ctx: Context,
        project_id: str,
        branch_name: str,
        ref: str,
    ) -> dict[str, Any]:
        """Create a new branch in a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            branch_name: Name for the new branch
            ref: Branch name or commit SHA to create the branch from

        Returns:
            Created branch object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_branch(project_id, branch_name, ref)

    @app.tool()
    async def delete_branch(
        ctx: Context,
        project_id: str,
        branch_name: str,
    ) -> dict[str, str]:
        """Delete a branch from a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            branch_name: Name of the branch to delete

        Returns:
            Confirmation message
        """
        client = await get_gitlab_client_for_context(ctx, config)
        await client.delete_branch(project_id, branch_name)
        return {"status": "deleted", "branch": branch_name}


def _register_tag_tools(app: Any, config: Config) -> None:
    """Register tag-related tools."""

    @app.tool()
    async def list_tags(
        ctx: Context,
        project_id: str,
        search: str | None = None,
        order_by: str = "updated",
        sort: str = "desc",
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List tags in a GitLab project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            search: Search term for tag names
            order_by: Order by field (name, updated)
            sort: Sort direction (asc, desc)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of tag objects with name, message, commit info, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        tags = await client.list_tags(
            project_id,
            search=search,
            order_by=order_by,
            sort=sort,
            per_page=per_page,
            max_pages=max_pages,
        )
        return tags[:max_items]

    @app.tool()
    async def get_tag(
        ctx: Context,
        project_id: str,
        tag_name: str,
    ) -> dict[str, Any]:
        """Get details of a specific tag.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            tag_name: Name of the tag

        Returns:
            Tag object with name, message, commit info, release info, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_tag(project_id, tag_name)

    @app.tool()
    async def create_tag(
        ctx: Context,
        project_id: str,
        tag_name: str,
        ref: str,
        message: str | None = None,
        release_description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new tag in a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            tag_name: Name for the new tag
            ref: Branch name or commit SHA to create the tag from
            message: Tag message (creates an annotated tag if provided)
            release_description: Release notes (creates a release if provided)

        Returns:
            Created tag object
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_tag(
            project_id,
            tag_name,
            ref,
            message=message,
            release_description=release_description,
        )

    @app.tool()
    async def delete_tag(
        ctx: Context,
        project_id: str,
        tag_name: str,
    ) -> dict[str, str]:
        """Delete a tag from a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            tag_name: Name of the tag to delete

        Returns:
            Confirmation message
        """
        client = await get_gitlab_client_for_context(ctx, config)
        await client.delete_tag(project_id, tag_name)
        return {"status": "deleted", "tag": tag_name}


def _register_compare_tools(app: Any, config: Config) -> None:
    """Register comparison tools."""

    @app.tool()
    async def compare_branches(
        ctx: Context,
        project_id: str,
        from_ref: str,
        to_ref: str,
        straight: bool = False,
    ) -> dict[str, Any]:
        """Compare two branches, tags, or commits.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            from_ref: Base branch, tag, or commit SHA
            to_ref: Target branch, tag, or commit SHA
            straight: If true, use straight comparison instead of merge-base

        Returns:
            Comparison object with commits list and diffs
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.compare_branches(project_id, from_ref, to_ref, straight)


def _register_tree_tools(app: Any, config: Config) -> None:
    """Register repository tree tools."""

    @app.tool()
    async def list_repository_tree(
        ctx: Context,
        project_id: str,
        path: str | None = None,
        ref: str | None = None,
        recursive: bool = False,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List files and directories in a repository.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            path: Path inside repository (root if not specified)
            ref: Branch, tag, or commit to list from (default branch if not specified)
            recursive: If true, list recursively
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of tree entries with id, name, type (blob/tree), path, mode
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        tree = await client.list_repository_tree(
            project_id,
            path=path,
            ref=ref,
            recursive=recursive,
            per_page=per_page,
            max_pages=max_pages,
        )
        return tree[:max_items]


def _register_file_tools(app: Any, config: Config) -> None:
    """Register file operation tools."""

    @app.tool()
    async def get_file(
        ctx: Context,
        project_id: str,
        file_path: str,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Get file metadata and content from a repository.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path to the file in the repository
            ref: Branch, tag, or commit (default branch if not specified)

        Returns:
            File object with file_name, file_path, size, encoding, content
            (base64), content_sha256, ref, blob_id, commit_id, last_commit_id
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_file(project_id, file_path, ref)

    @app.tool()
    async def get_file_content(
        ctx: Context,
        project_id: str,
        file_path: str,
        ref: str | None = None,
    ) -> dict[str, str]:
        """Get decoded file content from a repository.

        This is a convenience tool that returns the decoded file content
        directly, rather than base64-encoded content.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path to the file in the repository
            ref: Branch, tag, or commit (default branch if not specified)

        Returns:
            Dictionary with file_path and decoded content
        """
        client = await get_gitlab_client_for_context(ctx, config)
        content = await client.get_file_content(project_id, file_path, ref)
        return {"file_path": file_path, "content": content}

    @app.tool()
    async def create_file(
        ctx: Context,
        project_id: str,
        file_path: str,
        branch: str,
        content: str,
        commit_message: str,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new file in a repository.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path for the new file
            branch: Branch to create the file in
            content: File content (plain text)
            commit_message: Commit message for the change
            author_name: Override author name (optional)

        Returns:
            Created file info with file_path, branch, commit_id
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.create_file(
            project_id,
            file_path,
            branch,
            content,
            commit_message,
            author_name=author_name,
        )

    @app.tool()
    async def update_file(
        ctx: Context,
        project_id: str,
        file_path: str,
        branch: str,
        content: str,
        commit_message: str,
        author_name: str | None = None,
        last_commit_id: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing file in a repository.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path to the existing file
            branch: Branch containing the file
            content: New file content (plain text)
            commit_message: Commit message for the change
            author_name: Override author name (optional)
            last_commit_id: Expected last commit ID (for conflict detection)

        Returns:
            Updated file info with file_path, branch, commit_id
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.update_file(
            project_id,
            file_path,
            branch,
            content,
            commit_message,
            author_name=author_name,
            last_commit_id=last_commit_id,
        )

    @app.tool()
    async def delete_file(
        ctx: Context,
        project_id: str,
        file_path: str,
        branch: str,
        commit_message: str,
        author_name: str | None = None,
    ) -> dict[str, str]:
        """Delete a file from a repository.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path to the file to delete
            branch: Branch containing the file
            commit_message: Commit message for the deletion
            author_name: Override author name (optional)

        Returns:
            Confirmation with file_path and status
        """
        client = await get_gitlab_client_for_context(ctx, config)
        await client.delete_file(
            project_id,
            file_path,
            branch,
            commit_message,
            author_name=author_name,
        )
        return {"status": "deleted", "file_path": file_path}

    @app.tool()
    async def get_file_blame(
        ctx: Context,
        project_id: str,
        file_path: str,
        ref: str | None = None,
        range_start: int | None = None,
        range_end: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get blame information for a file.

        Shows which commit last modified each line of the file.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            file_path: Path to the file
            ref: Branch, tag, or commit (default branch if not specified)
            range_start: Starting line number (1-based)
            range_end: Ending line number (1-based)

        Returns:
            List of blame entries with commit info and lines
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_file_blame(
            project_id, file_path, ref, range_start, range_end
        )


def _register_commit_tools(app: Any, config: Config) -> None:
    """Register commit-related tools."""

    @app.tool()
    async def list_commits(
        ctx: Context,
        project_id: str,
        ref_name: str | None = None,
        since: str | None = None,
        until: str | None = None,
        path: str | None = None,
        author: str | None = None,
        with_stats: bool = False,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """List commits in a project.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            ref_name: Branch, tag, or commit to start from
            since: Only commits after this date (ISO 8601 format)
            until: Only commits before this date (ISO 8601 format)
            path: Only commits affecting this file path
            author: Only commits by this author (email or username)
            with_stats: Include commit stats (additions, deletions)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of commit objects with id, message, author info, etc.
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        commits = await client.list_commits(
            project_id,
            ref_name=ref_name,
            since=since,
            until=until,
            path=path,
            author=author,
            with_stats=with_stats,
            per_page=per_page,
            max_pages=max_pages,
        )
        return commits[:max_items]

    @app.tool()
    async def get_commit(
        ctx: Context,
        project_id: str,
        sha: str,
        stats: bool = True,
    ) -> dict[str, Any]:
        """Get details of a specific commit.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            sha: Commit SHA (full or short)
            stats: Include commit stats (additions, deletions)

        Returns:
            Commit object with full details including id, short_id, title,
            message, author_name, author_email, committer info, created_at,
            parent_ids, and stats
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_commit(project_id, sha, stats)

    @app.tool()
    async def get_commit_diff(
        ctx: Context,
        project_id: str,
        sha: str,
        per_page: int = 20,
        max_items: int = 100,
    ) -> list[dict[str, Any]]:
        """Get the diff of a commit.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            sha: Commit SHA (full or short)
            per_page: Results per page (max 100)
            max_items: Maximum total items to return

        Returns:
            List of diff entries with old_path, new_path, diff content,
            new_file, renamed_file, deleted_file flags
        """
        client = await get_gitlab_client_for_context(ctx, config)
        max_pages = (max_items + per_page - 1) // per_page
        diffs = await client.get_commit_diff(
            project_id, sha, per_page=per_page, max_pages=max_pages
        )
        return diffs[:max_items]

    @app.tool()
    async def cherry_pick_commit(
        ctx: Context,
        project_id: str,
        sha: str,
        branch: str,
        dry_run: bool = False,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Cherry-pick a commit to a branch.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            sha: Commit SHA to cherry-pick
            branch: Target branch name
            dry_run: If true, only check if cherry-pick is possible
            message: Custom commit message (optional)

        Returns:
            Cherry-picked commit object (or dry run result)
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.cherry_pick_commit(
            project_id, sha, branch, dry_run=dry_run, message=message
        )

    @app.tool()
    async def get_commit_refs(
        ctx: Context,
        project_id: str,
        sha: str,
        ref_type: str = "all",
    ) -> list[dict[str, Any]]:
        """Get branches and tags containing a commit.

        Args:
            ctx: Request context (injected automatically)
            project_id: Project ID or path (e.g., "mygroup/myproject")
            sha: Commit SHA
            ref_type: Type of refs to return (branch, tag, all)

        Returns:
            List of ref objects with type and name
        """
        client = await get_gitlab_client_for_context(ctx, config)
        return await client.get_commit_refs(project_id, sha, ref_type)
