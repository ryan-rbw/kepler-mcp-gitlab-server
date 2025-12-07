"""Tests for GitLab API client."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from kepler_mcp_gitlab.gitlab.client import (
    GitLabClient,
    GitLabNoAuthStrategy,
)
from kepler_mcp_gitlab.gitlab.exceptions import (
    GitLabAuthenticationError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabValidationError,
)


@pytest.fixture
def mock_auth_strategy() -> GitLabNoAuthStrategy:
    """Create a no-auth strategy for testing."""
    return GitLabNoAuthStrategy()


@pytest.fixture
def client(mock_auth_strategy: GitLabNoAuthStrategy) -> GitLabClient:
    """Create a GitLab client for testing."""
    return GitLabClient("https://gitlab.example.com", mock_auth_strategy)


class TestGitLabAuthStrategies:
    """Tests for GitLab auth strategies."""

    async def test_no_auth_strategy(self) -> None:
        """Test NoAuthStrategy returns empty headers."""
        strategy = GitLabNoAuthStrategy()
        headers = await strategy.get_auth_headers()
        assert headers == {}

    async def test_oauth_auth_strategy(self) -> None:
        """Test OAuthAuthStrategy returns Bearer token header."""
        from unittest.mock import AsyncMock, MagicMock

        from kepler_mcp_gitlab.gitlab.client import GitLabOAuthAuthStrategy

        mock_session_manager = MagicMock()
        mock_session_manager.get_auth_headers_for_session = AsyncMock(
            return_value={"Authorization": "Bearer test-oauth-token"}
        )

        strategy = GitLabOAuthAuthStrategy(mock_session_manager, "session-123")
        headers = await strategy.get_auth_headers()
        assert headers == {"Authorization": "Bearer test-oauth-token"}
        mock_session_manager.get_auth_headers_for_session.assert_called_once_with(
            "session-123"
        )


class TestGitLabClientInit:
    """Tests for GitLab client initialization."""

    def test_client_init(self, mock_auth_strategy: GitLabNoAuthStrategy) -> None:
        """Test client initializes with correct base URL."""
        client = GitLabClient("https://gitlab.example.com", mock_auth_strategy)
        assert client._base_url == "https://gitlab.example.com"
        assert client._api_url == "https://gitlab.example.com/api/v4"

    def test_client_init_strips_trailing_slash(
        self, mock_auth_strategy: GitLabNoAuthStrategy
    ) -> None:
        """Test client strips trailing slash from URL."""
        client = GitLabClient("https://gitlab.example.com/", mock_auth_strategy)
        assert client._base_url == "https://gitlab.example.com"

    def test_encode_project_id_numeric(self) -> None:
        """Test encoding numeric project ID."""
        assert GitLabClient._encode_project_id(123) == "123"

    def test_encode_project_id_path(self) -> None:
        """Test encoding project path."""
        assert GitLabClient._encode_project_id("group/project") == "group%2Fproject"

    def test_encode_project_id_nested_path(self) -> None:
        """Test encoding nested project path."""
        result = GitLabClient._encode_project_id("org/group/subgroup/project")
        assert result == "org%2Fgroup%2Fsubgroup%2Fproject"


class TestGitLabClientProjects:
    """Tests for project-related API calls."""

    @respx.mock
    async def test_list_projects(self, client: GitLabClient) -> None:
        """Test listing projects."""
        mock_projects = [
            {"id": 1, "name": "Project 1", "path": "project-1"},
            {"id": 2, "name": "Project 2", "path": "project-2"},
        ]
        respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(200, json=mock_projects)
        )

        projects = await client.list_projects()
        assert len(projects) == 2
        assert projects[0]["name"] == "Project 1"

    @respx.mock
    async def test_list_projects_with_search(self, client: GitLabClient) -> None:
        """Test listing projects with search filter."""
        mock_projects = [{"id": 1, "name": "Test Project", "path": "test-project"}]
        route = respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(200, json=mock_projects)
        )

        projects = await client.list_projects(search="test")
        assert len(projects) == 1
        assert "search=test" in str(route.calls[0].request.url)

    @respx.mock
    async def test_get_project(self, client: GitLabClient) -> None:
        """Test getting a single project."""
        mock_project = {
            "id": 1,
            "name": "Test Project",
            "path": "test-project",
            "description": "A test project",
        }
        respx.get("https://gitlab.example.com/api/v4/projects/1").mock(
            return_value=Response(200, json=mock_project)
        )

        project = await client.get_project(1)
        assert project["name"] == "Test Project"

    @respx.mock
    async def test_get_project_by_path(self, client: GitLabClient) -> None:
        """Test getting a project by path."""
        mock_project = {"id": 1, "name": "Test Project"}
        respx.get("https://gitlab.example.com/api/v4/projects/group%2Fproject").mock(
            return_value=Response(200, json=mock_project)
        )

        project = await client.get_project("group/project")
        assert project["id"] == 1

    @respx.mock
    async def test_get_project_languages(self, client: GitLabClient) -> None:
        """Test getting project languages."""
        mock_languages = {"Python": 75.5, "JavaScript": 20.0, "Shell": 4.5}
        respx.get("https://gitlab.example.com/api/v4/projects/1/languages").mock(
            return_value=Response(200, json=mock_languages)
        )

        languages = await client.get_project_languages(1)
        assert languages["Python"] == 75.5


class TestGitLabClientIssues:
    """Tests for issue-related API calls."""

    @respx.mock
    async def test_list_issues(self, client: GitLabClient) -> None:
        """Test listing issues."""
        mock_issues = [
            {"id": 1, "iid": 1, "title": "Issue 1", "state": "opened"},
            {"id": 2, "iid": 2, "title": "Issue 2", "state": "closed"},
        ]
        respx.get("https://gitlab.example.com/api/v4/projects/1/issues").mock(
            return_value=Response(200, json=mock_issues)
        )

        issues = await client.list_issues(1)
        assert len(issues) == 2
        assert issues[0]["title"] == "Issue 1"

    @respx.mock
    async def test_get_issue(self, client: GitLabClient) -> None:
        """Test getting a single issue."""
        mock_issue = {
            "id": 1,
            "iid": 42,
            "title": "Test Issue",
            "description": "Issue description",
            "state": "opened",
        }
        respx.get("https://gitlab.example.com/api/v4/projects/1/issues/42").mock(
            return_value=Response(200, json=mock_issue)
        )

        issue = await client.get_issue(1, 42)
        assert issue["iid"] == 42
        assert issue["title"] == "Test Issue"

    @respx.mock
    async def test_create_issue(self, client: GitLabClient) -> None:
        """Test creating an issue."""
        mock_issue = {
            "id": 1,
            "iid": 1,
            "title": "New Issue",
            "description": "Description",
            "state": "opened",
        }
        route = respx.post("https://gitlab.example.com/api/v4/projects/1/issues").mock(
            return_value=Response(201, json=mock_issue)
        )

        issue = await client.create_issue(
            project_id=1,
            title="New Issue",
            description="Description",
        )
        assert issue["title"] == "New Issue"
        assert route.called

    @respx.mock
    async def test_update_issue(self, client: GitLabClient) -> None:
        """Test updating an issue."""
        mock_issue = {
            "id": 1,
            "iid": 42,
            "title": "Updated Title",
            "state": "opened",
        }
        respx.put("https://gitlab.example.com/api/v4/projects/1/issues/42").mock(
            return_value=Response(200, json=mock_issue)
        )

        issue = await client.update_issue(1, 42, title="Updated Title")
        assert issue["title"] == "Updated Title"

    @respx.mock
    async def test_create_issue_note(self, client: GitLabClient) -> None:
        """Test adding a comment to an issue."""
        mock_note = {
            "id": 1,
            "body": "Test comment",
            "author": {"id": 1, "username": "testuser"},
        }
        respx.post("https://gitlab.example.com/api/v4/projects/1/issues/42/notes").mock(
            return_value=Response(201, json=mock_note)
        )

        note = await client.create_issue_note(1, 42, "Test comment")
        assert note["body"] == "Test comment"


class TestGitLabClientMergeRequests:
    """Tests for merge request-related API calls."""

    @respx.mock
    async def test_list_merge_requests(self, client: GitLabClient) -> None:
        """Test listing merge requests."""
        mock_mrs = [
            {"id": 1, "iid": 1, "title": "MR 1", "state": "opened"},
            {"id": 2, "iid": 2, "title": "MR 2", "state": "merged"},
        ]
        respx.get("https://gitlab.example.com/api/v4/projects/1/merge_requests").mock(
            return_value=Response(200, json=mock_mrs)
        )

        mrs = await client.list_merge_requests(1)
        assert len(mrs) == 2
        assert mrs[0]["title"] == "MR 1"

    @respx.mock
    async def test_get_merge_request(self, client: GitLabClient) -> None:
        """Test getting a single merge request."""
        mock_mr = {
            "id": 1,
            "iid": 42,
            "title": "Test MR",
            "source_branch": "feature",
            "target_branch": "main",
            "state": "opened",
        }
        respx.get("https://gitlab.example.com/api/v4/projects/1/merge_requests/42").mock(
            return_value=Response(200, json=mock_mr)
        )

        mr = await client.get_merge_request(1, 42)
        assert mr["iid"] == 42
        assert mr["source_branch"] == "feature"

    @respx.mock
    async def test_create_merge_request(self, client: GitLabClient) -> None:
        """Test creating a merge request."""
        mock_mr = {
            "id": 1,
            "iid": 1,
            "title": "New MR",
            "source_branch": "feature",
            "target_branch": "main",
            "state": "opened",
        }
        respx.post("https://gitlab.example.com/api/v4/projects/1/merge_requests").mock(
            return_value=Response(201, json=mock_mr)
        )

        mr = await client.create_merge_request(
            project_id=1,
            source_branch="feature",
            target_branch="main",
            title="New MR",
        )
        assert mr["title"] == "New MR"

    @respx.mock
    async def test_merge_merge_request(self, client: GitLabClient) -> None:
        """Test merging a merge request."""
        mock_mr = {
            "id": 1,
            "iid": 42,
            "title": "Test MR",
            "state": "merged",
        }
        respx.put("https://gitlab.example.com/api/v4/projects/1/merge_requests/42/merge").mock(
            return_value=Response(200, json=mock_mr)
        )

        mr = await client.merge_merge_request(1, 42)
        assert mr["state"] == "merged"

    @respx.mock
    async def test_approve_merge_request(self, client: GitLabClient) -> None:
        """Test approving a merge request."""
        mock_approval = {"id": 1, "iid": 42, "approved": True}
        respx.post(
            "https://gitlab.example.com/api/v4/projects/1/merge_requests/42/approve"
        ).mock(return_value=Response(200, json=mock_approval))

        result = await client.approve_merge_request(1, 42)
        assert result["approved"] is True

    @respx.mock
    async def test_get_merge_request_changes(self, client: GitLabClient) -> None:
        """Test getting merge request changes."""
        mock_changes = {
            "id": 1,
            "iid": 42,
            "changes": [
                {"old_path": "file.py", "new_path": "file.py", "diff": "@@ -1 +1 @@"}
            ],
        }
        respx.get(
            "https://gitlab.example.com/api/v4/projects/1/merge_requests/42/changes"
        ).mock(return_value=Response(200, json=mock_changes))

        result = await client.get_merge_request_changes(1, 42)
        assert len(result["changes"]) == 1


class TestGitLabClientErrors:
    """Tests for error handling."""

    @respx.mock
    async def test_authentication_error(self, client: GitLabClient) -> None:
        """Test handling 401 authentication error."""
        respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(401, json={"message": "401 Unauthorized"})
        )

        with pytest.raises(GitLabAuthenticationError) as exc_info:
            await client.list_projects()
        assert exc_info.value.status_code == 401

    @respx.mock
    async def test_not_found_error(self, client: GitLabClient) -> None:
        """Test handling 404 not found error."""
        respx.get("https://gitlab.example.com/api/v4/projects/999").mock(
            return_value=Response(404, json={"message": "404 Project Not Found"})
        )

        with pytest.raises(GitLabNotFoundError) as exc_info:
            await client.get_project(999)
        assert exc_info.value.status_code == 404

    @respx.mock
    async def test_rate_limit_error(self, client: GitLabClient) -> None:
        """Test handling 429 rate limit error."""
        respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(
                429,
                json={"message": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(GitLabRateLimitError) as exc_info:
            await client.list_projects()
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60

    @respx.mock
    async def test_validation_error(self, client: GitLabClient) -> None:
        """Test handling 400 validation error."""
        respx.post("https://gitlab.example.com/api/v4/projects/1/issues").mock(
            return_value=Response(400, json={"message": "title is required"})
        )

        with pytest.raises(GitLabValidationError) as exc_info:
            await client.create_issue(1, title="")
        assert exc_info.value.status_code == 400


class TestGitLabClientPagination:
    """Tests for pagination handling."""

    @respx.mock
    async def test_pagination_single_page(self, client: GitLabClient) -> None:
        """Test pagination with single page of results."""
        mock_projects = [{"id": i, "name": f"Project {i}"} for i in range(5)]
        respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(200, json=mock_projects)
        )

        projects = await client.list_projects(per_page=20)
        assert len(projects) == 5

    @respx.mock
    async def test_pagination_multiple_pages(self, client: GitLabClient) -> None:
        """Test pagination with multiple pages."""
        page1 = [{"id": i, "name": f"Project {i}"} for i in range(1, 21)]
        page2 = [{"id": i, "name": f"Project {i}"} for i in range(21, 31)]

        route = respx.get("https://gitlab.example.com/api/v4/projects")
        route.side_effect = [
            Response(200, json=page1),
            Response(200, json=page2),
        ]

        projects = await client.list_projects(per_page=20, max_pages=2)
        assert len(projects) == 30

    @respx.mock
    async def test_pagination_max_pages_limit(self, client: GitLabClient) -> None:
        """Test pagination respects max_pages limit."""
        page1 = [{"id": i, "name": f"Project {i}"} for i in range(1, 21)]

        respx.get("https://gitlab.example.com/api/v4/projects").mock(
            return_value=Response(200, json=page1)
        )

        projects = await client.list_projects(per_page=20, max_pages=1)
        assert len(projects) == 20


class TestGitLabClientUser:
    """Tests for user-related API calls."""

    @respx.mock
    async def test_get_current_user(self, client: GitLabClient) -> None:
        """Test getting current user."""
        mock_user = {
            "id": 1,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        }
        respx.get("https://gitlab.example.com/api/v4/user").mock(
            return_value=Response(200, json=mock_user)
        )

        user = await client.get_current_user()
        assert user["username"] == "testuser"
