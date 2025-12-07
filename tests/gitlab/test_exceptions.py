"""Tests for GitLab exceptions."""

from __future__ import annotations

from kepler_mcp_gitlab.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthenticationError,
    GitLabConflictError,
    GitLabForbiddenError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabValidationError,
)


class TestGitLabAPIError:
    """Tests for base GitLabAPIError."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = GitLabAPIError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.response_body is None

    def test_error_with_status_code(self) -> None:
        """Test error with status code."""
        error = GitLabAPIError("Server error", status_code=500)
        assert str(error) == "[500] Server error"
        assert error.status_code == 500

    def test_error_with_response_body(self) -> None:
        """Test error with response body."""
        body = {"error": "details"}
        error = GitLabAPIError("Error", status_code=400, response_body=body)
        assert error.response_body == body


class TestGitLabAuthenticationError:
    """Tests for GitLabAuthenticationError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabAuthenticationError()
        assert "Authentication failed" in error.message
        assert error.status_code == 401

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = GitLabAuthenticationError("Invalid token")
        assert error.message == "Invalid token"
        assert error.status_code == 401


class TestGitLabNotFoundError:
    """Tests for GitLabNotFoundError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabNotFoundError()
        assert "not found" in error.message.lower()
        assert error.status_code == 404

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = GitLabNotFoundError("Project not found")
        assert error.message == "Project not found"


class TestGitLabRateLimitError:
    """Tests for GitLabRateLimitError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabRateLimitError()
        assert "Rate limit" in error.message
        assert error.status_code == 429
        assert error.retry_after is None

    def test_with_retry_after(self) -> None:
        """Test error with retry_after value."""
        error = GitLabRateLimitError(retry_after=60)
        assert error.retry_after == 60


class TestGitLabValidationError:
    """Tests for GitLabValidationError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabValidationError()
        assert "validation" in error.message.lower()
        assert error.status_code == 400


class TestGitLabForbiddenError:
    """Tests for GitLabForbiddenError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabForbiddenError()
        assert "forbidden" in error.message.lower()
        assert error.status_code == 403


class TestGitLabConflictError:
    """Tests for GitLabConflictError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = GitLabConflictError()
        assert "conflict" in error.message.lower()
        assert error.status_code == 409
