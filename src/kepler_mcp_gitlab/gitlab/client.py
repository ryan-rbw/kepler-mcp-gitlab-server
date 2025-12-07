"""GitLab API client.

Provides an async HTTP client for interacting with the GitLab REST API.
"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

import httpx

from kepler_mcp_gitlab.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthenticationError,
    GitLabConflictError,
    GitLabForbiddenError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabValidationError,
)
from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.security import AuthStrategy

if TYPE_CHECKING:
    from kepler_mcp_gitlab.oauth.session import SessionManager

logger = get_logger(__name__)

# Default timeout for API requests (seconds)
DEFAULT_TIMEOUT = 30.0

# Default pagination settings
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


class GitLabOAuthAuthStrategy(AuthStrategy):
    """Authentication strategy using GitLab OAuth tokens via session.

    Delegates to SessionManager to get valid OAuth tokens, which handles
    automatic token refresh. Uses Authorization: Bearer format.
    """

    def __init__(self, session_manager: SessionManager, session_id: str) -> None:
        """Initialize with session manager and session ID.

        Args:
            session_manager: SessionManager instance with token store
            session_id: ID of the authenticated session
        """
        self._session_manager = session_manager
        self._session_id = session_id

    async def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers from the session.

        Returns:
            Authorization headers with current valid OAuth token

        Raises:
            GitLabAuthenticationError: If session is invalid or token refresh fails
        """
        try:
            return await self._session_manager.get_auth_headers_for_session(self._session_id)
        except Exception as e:
            logger.error("Failed to get auth headers for session %s: %s", self._session_id, e)
            raise GitLabAuthenticationError(f"Session authentication failed: {e}") from e


class GitLabNoAuthStrategy(AuthStrategy):
    """Authentication strategy for unauthenticated requests.

    Only works for public GitLab resources.
    """

    async def get_auth_headers(self) -> dict[str, str]:
        """Return empty headers."""
        return {}


class GitLabClient:
    """Async client for GitLab REST API.

    This client handles:
    - Authentication via AuthStrategy (OAuth, PAT, or no auth)
    - Automatic pagination
    - Error handling and exception mapping
    - URL encoding for project paths

    Example:
        ```python
        # With OAuth session auth
        auth_strategy = SessionAuthStrategy(session_manager, session_id)
        client = GitLabClient("https://gitlab.com", auth_strategy)

        # Make API calls
        projects = await client.list_projects(owned=True)
        issue = await client.get_issue("mygroup/myproject", 42)
        ```
    """

    def __init__(self, base_url: str, auth_strategy: AuthStrategy) -> None:
        """Initialize the GitLab client.

        Args:
            base_url: GitLab instance base URL (e.g., "https://gitlab.com")
            auth_strategy: Authentication strategy for API requests
        """
        self._base_url = base_url.rstrip("/")
        self._api_url = f"{self._base_url}/api/v4"
        self._auth_strategy = auth_strategy
        self._client: httpx.AsyncClient | None = None

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return await self._auth_strategy.get_auth_headers()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Note: Auth headers are fetched per-request to support token refresh.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _encode_project_id(project_id: str | int) -> str:
        """URL-encode a project ID or path.

        GitLab accepts either numeric IDs or URL-encoded paths like "group%2Fproject".

        Args:
            project_id: Numeric ID or path like "mygroup/myproject"

        Returns:
            URL-encoded project identifier
        """
        if isinstance(project_id, int):
            return str(project_id)
        # URL-encode the path (e.g., "group/project" -> "group%2Fproject")
        return urllib.parse.quote(project_id, safe="")

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API.

        Args:
            response: HTTP response object

        Raises:
            GitLabAPIError: Appropriate exception based on status code
        """
        status = response.status_code

        # Try to parse error body
        try:
            body = response.json()
            if isinstance(body, dict):
                message = body.get("message") or body.get("error") or str(body)
            else:
                message = str(body)
        except Exception:
            message = response.text or f"HTTP {status}"

        if status == 401:
            raise GitLabAuthenticationError(message, status, body if "body" in dir() else None)
        if status == 403:
            raise GitLabForbiddenError(message, status, body if "body" in dir() else None)
        if status == 404:
            raise GitLabNotFoundError(message, status, body if "body" in dir() else None)
        if status == 409:
            raise GitLabConflictError(message, status, body if "body" in dir() else None)
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise GitLabRateLimitError(
                message,
                status,
                body if "body" in dir() else None,
                int(retry_after) if retry_after else None,
            )
        if status == 400:
            raise GitLabValidationError(message, status, body if "body" in dir() else None)

        raise GitLabAPIError(message, status, body if "body" in dir() else None)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (without base URL)
            params: Query parameters
            json_data: JSON body for POST/PUT requests

        Returns:
            Parsed JSON response

        Raises:
            GitLabAPIError: On API errors
        """
        client = await self._get_client()
        url = f"{self._api_url}{path}"

        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        # Get auth headers per-request (supports token refresh)
        auth_headers = await self._get_auth_headers()

        logger.debug("GitLab API request: %s %s", method, path)

        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=auth_headers,
        )

        if not response.is_success:
            self._handle_error_response(response)

        # Handle empty responses (e.g., DELETE returns 204)
        if response.status_code == 204 or not response.content:
            return None

        return response.json()

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a GET request."""
        return await self._request("GET", path, params=params)

    async def _post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a POST request."""
        return await self._request("POST", path, params=params, json_data=json_data)

    async def _put(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a PUT request."""
        return await self._request("PUT", path, params=params, json_data=json_data)

    async def _delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a DELETE request."""
        return await self._request("DELETE", path, params=params)

    async def _paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = None,
    ) -> list[Any]:
        """Fetch all pages of a paginated endpoint.

        Args:
            path: API path
            params: Query parameters
            per_page: Results per page (max 100)
            max_pages: Maximum number of pages to fetch (None for all)

        Returns:
            Combined list of all results
        """
        params = params or {}
        params["per_page"] = min(per_page, MAX_PER_PAGE)
        params["page"] = 1

        results: list[Any] = []
        pages_fetched = 0

        while True:
            page_results = await self._get(path, params)

            if not isinstance(page_results, list):
                # Single result, not paginated
                return [page_results] if page_results else []

            results.extend(page_results)
            pages_fetched += 1

            # Check if we've reached max pages or got fewer results than requested
            if max_pages and pages_fetched >= max_pages:
                break
            if len(page_results) < params["per_page"]:
                break

            params["page"] += 1

        return results

    # -------------------------------------------------------------------------
    # Project endpoints
    # -------------------------------------------------------------------------

    async def list_projects(
        self,
        search: str | None = None,
        visibility: str | None = None,
        owned: bool = False,
        membership: bool = False,
        archived: bool | None = None,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List projects accessible to the authenticated user.

        Args:
            search: Search term for project name, path, or description
            visibility: Filter by visibility (public, internal, private)
            owned: Only return projects owned by the user
            membership: Only return projects user is a member of
            archived: Filter by archived status
            order_by: Order by field (id, name, path, created_at, updated_at, last_activity_at)
            sort: Sort direction (asc, desc)
            per_page: Results per page
            max_pages: Maximum pages to fetch (None for all)

        Returns:
            List of project dictionaries
        """
        params: dict[str, Any] = {
            "search": search,
            "visibility": visibility,
            "owned": owned if owned else None,
            "membership": membership if membership else None,
            "archived": archived,
            "order_by": order_by,
            "sort": sort,
        }
        return await self._paginate("/projects", params, per_page, max_pages)

    async def get_project(
        self,
        project_id: str | int,
        statistics: bool = False,
        with_custom_attributes: bool = False,
    ) -> dict[str, Any]:
        """Get details of a specific project.

        Args:
            project_id: Project ID or URL-encoded path (e.g., "mygroup/myproject")
            statistics: Include project statistics
            with_custom_attributes: Include custom attributes

        Returns:
            Project details dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        params = {
            "statistics": statistics if statistics else None,
            "with_custom_attributes": with_custom_attributes if with_custom_attributes else None,
        }
        result = await self._get(f"/projects/{encoded_id}", params)
        return dict(result)

    async def get_project_languages(self, project_id: str | int) -> dict[str, float]:
        """Get programming languages used in a project.

        Args:
            project_id: Project ID or URL-encoded path

        Returns:
            Dictionary mapping language names to percentage usage
        """
        encoded_id = self._encode_project_id(project_id)
        result = await self._get(f"/projects/{encoded_id}/languages")
        return dict(result)

    # -------------------------------------------------------------------------
    # Issue endpoints
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        project_id: str | int,
        state: str | None = None,
        labels: str | None = None,
        milestone: str | None = None,
        assignee_id: int | None = None,
        author_id: int | None = None,
        search: str | None = None,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List issues in a project.

        Args:
            project_id: Project ID or URL-encoded path
            state: Filter by state (opened, closed, all)
            labels: Comma-separated list of label names
            milestone: Milestone title
            assignee_id: Filter by assignee user ID
            author_id: Filter by author user ID
            search: Search in title and description
            order_by: Order by field
            sort: Sort direction
            per_page: Results per page
            max_pages: Maximum pages to fetch

        Returns:
            List of issue dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        params: dict[str, Any] = {
            "state": state,
            "labels": labels,
            "milestone": milestone,
            "assignee_id": assignee_id,
            "author_id": author_id,
            "search": search,
            "order_by": order_by,
            "sort": sort,
        }
        return await self._paginate(f"/projects/{encoded_id}/issues", params, per_page, max_pages)

    async def get_issue(
        self,
        project_id: str | int,
        issue_iid: int,
    ) -> dict[str, Any]:
        """Get a single issue.

        Args:
            project_id: Project ID or URL-encoded path
            issue_iid: Issue internal ID (IID)

        Returns:
            Issue details dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        result = await self._get(f"/projects/{encoded_id}/issues/{issue_iid}")
        return dict(result)

    async def create_issue(
        self,
        project_id: str | int,
        title: str,
        description: str | None = None,
        labels: str | None = None,
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
        confidential: bool = False,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue.

        Args:
            project_id: Project ID or URL-encoded path
            title: Issue title
            description: Issue description (Markdown supported)
            labels: Comma-separated list of label names
            assignee_ids: List of user IDs to assign
            milestone_id: Milestone ID
            confidential: Whether issue is confidential
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Created issue dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "title": title,
            "description": description,
            "labels": labels,
            "assignee_ids": assignee_ids,
            "milestone_id": milestone_id,
            "confidential": confidential,
            "due_date": due_date,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        result = await self._post(f"/projects/{encoded_id}/issues", json_data=data)
        return dict(result)

    async def update_issue(
        self,
        project_id: str | int,
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
            project_id: Project ID or URL-encoded path
            issue_iid: Issue internal ID (IID)
            title: New title
            description: New description
            state_event: State change (close, reopen)
            labels: Comma-separated list of label names (replaces existing)
            assignee_ids: List of user IDs to assign (replaces existing)
            milestone_id: Milestone ID (0 to unset)
            confidential: Whether issue is confidential
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Updated issue dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "title": title,
            "description": description,
            "state_event": state_event,
            "labels": labels,
            "assignee_ids": assignee_ids,
            "milestone_id": milestone_id,
            "confidential": confidential,
            "due_date": due_date,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        result = await self._put(f"/projects/{encoded_id}/issues/{issue_iid}", json_data=data)
        return dict(result)

    async def delete_issue(
        self,
        project_id: str | int,
        issue_iid: int,
    ) -> None:
        """Delete an issue.

        Args:
            project_id: Project ID or URL-encoded path
            issue_iid: Issue internal ID (IID)
        """
        encoded_id = self._encode_project_id(project_id)
        await self._delete(f"/projects/{encoded_id}/issues/{issue_iid}")

    async def list_issue_notes(
        self,
        project_id: str | int,
        issue_iid: int,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List comments (notes) on an issue.

        Args:
            project_id: Project ID or URL-encoded path
            issue_iid: Issue internal ID (IID)
            order_by: Order by field
            sort: Sort direction
            per_page: Results per page
            max_pages: Maximum pages to fetch

        Returns:
            List of note dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        params: dict[str, Any] = {
            "order_by": order_by,
            "sort": sort,
        }
        return await self._paginate(
            f"/projects/{encoded_id}/issues/{issue_iid}/notes",
            params,
            per_page,
            max_pages,
        )

    async def create_issue_note(
        self,
        project_id: str | int,
        issue_iid: int,
        body: str,
        confidential: bool = False,
    ) -> dict[str, Any]:
        """Add a comment (note) to an issue.

        Args:
            project_id: Project ID or URL-encoded path
            issue_iid: Issue internal ID (IID)
            body: Comment body (Markdown supported)
            confidential: Whether the note is confidential

        Returns:
            Created note dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data = {
            "body": body,
            "confidential": confidential,
        }
        result = await self._post(
            f"/projects/{encoded_id}/issues/{issue_iid}/notes",
            json_data=data,
        )
        return dict(result)

    # -------------------------------------------------------------------------
    # Merge Request endpoints
    # -------------------------------------------------------------------------

    async def list_merge_requests(
        self,
        project_id: str | int,
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
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List merge requests in a project.

        Args:
            project_id: Project ID or URL-encoded path
            state: Filter by state (opened, closed, merged, all)
            labels: Comma-separated list of label names
            milestone: Milestone title
            scope: Filter by scope (created_by_me, assigned_to_me, all)
            author_id: Filter by author user ID
            assignee_id: Filter by assignee user ID
            reviewer_id: Filter by reviewer user ID
            source_branch: Filter by source branch
            target_branch: Filter by target branch
            search: Search in title and description
            order_by: Order by field
            sort: Sort direction
            per_page: Results per page
            max_pages: Maximum pages to fetch

        Returns:
            List of merge request dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        params: dict[str, Any] = {
            "state": state,
            "labels": labels,
            "milestone": milestone,
            "scope": scope,
            "author_id": author_id,
            "assignee_id": assignee_id,
            "reviewer_id": reviewer_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "search": search,
            "order_by": order_by,
            "sort": sort,
        }
        return await self._paginate(
            f"/projects/{encoded_id}/merge_requests",
            params,
            per_page,
            max_pages,
        )

    async def get_merge_request(
        self,
        project_id: str | int,
        merge_request_iid: int,
        include_diverged_commits_count: bool = False,
        include_rebase_in_progress: bool = False,
    ) -> dict[str, Any]:
        """Get a single merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            include_diverged_commits_count: Include diverged commits count
            include_rebase_in_progress: Include rebase in progress status

        Returns:
            Merge request details dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        params = {
            "include_diverged_commits_count": (
                include_diverged_commits_count if include_diverged_commits_count else None
            ),
            "include_rebase_in_progress": (
                include_rebase_in_progress if include_rebase_in_progress else None
            ),
        }
        result = await self._get(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}",
            params,
        )
        return dict(result)

    async def create_merge_request(
        self,
        project_id: str | int,
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
            project_id: Project ID or URL-encoded path
            source_branch: Source branch name
            target_branch: Target branch name
            title: MR title
            description: MR description (Markdown supported)
            assignee_ids: List of user IDs to assign
            reviewer_ids: List of user IDs to request review
            labels: Comma-separated list of label names
            milestone_id: Milestone ID
            remove_source_branch: Remove source branch after merge
            squash: Squash commits on merge
            draft: Create as draft MR

        Returns:
            Created merge request dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "assignee_ids": assignee_ids,
            "reviewer_ids": reviewer_ids,
            "labels": labels,
            "milestone_id": milestone_id,
            "remove_source_branch": remove_source_branch,
            "squash": squash,
        }
        # Handle draft MR
        if draft and not title.startswith("Draft:") and not title.startswith("WIP:"):
            data["title"] = f"Draft: {title}"

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        result = await self._post(f"/projects/{encoded_id}/merge_requests", json_data=data)
        return dict(result)

    async def update_merge_request(
        self,
        project_id: str | int,
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
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            title: New title
            description: New description
            state_event: State change (close, reopen)
            target_branch: New target branch
            assignee_ids: List of user IDs to assign
            reviewer_ids: List of user IDs to request review
            labels: Comma-separated list of label names
            milestone_id: Milestone ID (0 to unset)
            remove_source_branch: Remove source branch after merge
            squash: Squash commits on merge

        Returns:
            Updated merge request dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "title": title,
            "description": description,
            "state_event": state_event,
            "target_branch": target_branch,
            "assignee_ids": assignee_ids,
            "reviewer_ids": reviewer_ids,
            "labels": labels,
            "milestone_id": milestone_id,
            "remove_source_branch": remove_source_branch,
            "squash": squash,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        result = await self._put(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}",
            json_data=data,
        )
        return dict(result)

    async def merge_merge_request(
        self,
        project_id: str | int,
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
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            merge_commit_message: Custom merge commit message
            squash_commit_message: Custom squash commit message
            squash: Squash commits before merging
            should_remove_source_branch: Remove source branch after merge
            merge_when_pipeline_succeeds: Merge when pipeline succeeds
            sha: Expected HEAD SHA of source branch (for optimistic locking)

        Returns:
            Merged merge request dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "merge_commit_message": merge_commit_message,
            "squash_commit_message": squash_commit_message,
            "squash": squash if squash else None,
            "should_remove_source_branch": (
                should_remove_source_branch if should_remove_source_branch else None
            ),
            "merge_when_pipeline_succeeds": (
                merge_when_pipeline_succeeds if merge_when_pipeline_succeeds else None
            ),
            "sha": sha,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        result = await self._put(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/merge",
            json_data=data,
        )
        return dict(result)

    async def approve_merge_request(
        self,
        project_id: str | int,
        merge_request_iid: int,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Approve a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            sha: Expected HEAD SHA of source branch (for optimistic locking)

        Returns:
            Approval result dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {}
        if sha:
            data["sha"] = sha
        result = await self._post(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/approve",
            json_data=data if data else None,
        )
        return dict(result)

    async def unapprove_merge_request(
        self,
        project_id: str | int,
        merge_request_iid: int,
    ) -> dict[str, Any]:
        """Remove approval from a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)

        Returns:
            Unapproval result dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        result = await self._post(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/unapprove",
        )
        return dict(result)

    async def get_merge_request_changes(
        self,
        project_id: str | int,
        merge_request_iid: int,
    ) -> dict[str, Any]:
        """Get the changes (diff) of a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)

        Returns:
            Merge request with changes dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        result = await self._get(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/changes",
        )
        return dict(result)

    async def list_merge_request_notes(
        self,
        project_id: str | int,
        merge_request_iid: int,
        order_by: str = "created_at",
        sort: str = "desc",
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List comments (notes) on a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            order_by: Order by field
            sort: Sort direction
            per_page: Results per page
            max_pages: Maximum pages to fetch

        Returns:
            List of note dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        params: dict[str, Any] = {
            "order_by": order_by,
            "sort": sort,
        }
        return await self._paginate(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/notes",
            params,
            per_page,
            max_pages,
        )

    async def create_merge_request_note(
        self,
        project_id: str | int,
        merge_request_iid: int,
        body: str,
    ) -> dict[str, Any]:
        """Add a comment (note) to a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            body: Comment body (Markdown supported)

        Returns:
            Created note dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data = {"body": body}
        result = await self._post(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/notes",
            json_data=data,
        )
        return dict(result)

    async def list_merge_request_discussions(
        self,
        project_id: str | int,
        merge_request_iid: int,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = 1,
    ) -> list[dict[str, Any]]:
        """List discussion threads on a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            per_page: Results per page
            max_pages: Maximum pages to fetch

        Returns:
            List of discussion dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        return await self._paginate(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/discussions",
            per_page=per_page,
            max_pages=max_pages,
        )

    async def resolve_merge_request_discussion(
        self,
        project_id: str | int,
        merge_request_iid: int,
        discussion_id: str,
        resolved: bool = True,
    ) -> dict[str, Any]:
        """Resolve or unresolve a merge request discussion thread.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)
            discussion_id: Discussion ID
            resolved: True to resolve, False to unresolve

        Returns:
            Updated discussion dictionary
        """
        encoded_id = self._encode_project_id(project_id)
        data = {"resolved": resolved}
        result = await self._put(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/discussions/{discussion_id}",
            json_data=data,
        )
        return dict(result)

    async def get_merge_request_participants(
        self,
        project_id: str | int,
        merge_request_iid: int,
    ) -> list[dict[str, Any]]:
        """Get participants in a merge request.

        Args:
            project_id: Project ID or URL-encoded path
            merge_request_iid: Merge request internal ID (IID)

        Returns:
            List of user dictionaries
        """
        encoded_id = self._encode_project_id(project_id)
        result = await self._get(
            f"/projects/{encoded_id}/merge_requests/{merge_request_iid}/participants",
        )
        return list(result)

    # -------------------------------------------------------------------------
    # User endpoints
    # -------------------------------------------------------------------------

    async def get_current_user(self) -> dict[str, Any]:
        """Get the currently authenticated user.

        Returns:
            Current user dictionary
        """
        result = await self._get("/user")
        return dict(result)
