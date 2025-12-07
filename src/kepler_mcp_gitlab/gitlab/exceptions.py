"""GitLab API exceptions."""

from __future__ import annotations


class GitLabAPIError(Exception):
    """Base exception for GitLab API errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (if applicable)
        response_body: Raw response body (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class GitLabAuthenticationError(GitLabAPIError):
    """Raised when authentication fails (401 Unauthorized)."""

    def __init__(
        self,
        message: str = "Authentication failed. Check your GitLab token.",
        status_code: int = 401,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class GitLabNotFoundError(GitLabAPIError):
    """Raised when a resource is not found (404 Not Found)."""

    def __init__(
        self,
        message: str = "Resource not found.",
        status_code: int = 404,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class GitLabRateLimitError(GitLabAPIError):
    """Raised when rate limit is exceeded (429 Too Many Requests).

    Attributes:
        retry_after: Seconds to wait before retrying (if provided by API)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded.",
        status_code: int = 429,
        response_body: dict | str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


class GitLabValidationError(GitLabAPIError):
    """Raised when request validation fails (400 Bad Request)."""

    def __init__(
        self,
        message: str = "Request validation failed.",
        status_code: int = 400,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class GitLabForbiddenError(GitLabAPIError):
    """Raised when access is forbidden (403 Forbidden)."""

    def __init__(
        self,
        message: str = "Access forbidden. Check your permissions.",
        status_code: int = 403,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class GitLabConflictError(GitLabAPIError):
    """Raised when there's a conflict (409 Conflict)."""

    def __init__(
        self,
        message: str = "Resource conflict.",
        status_code: int = 409,
        response_body: dict | str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
