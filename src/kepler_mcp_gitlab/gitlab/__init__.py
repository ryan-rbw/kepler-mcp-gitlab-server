"""GitLab API client and utilities."""

from kepler_mcp_gitlab.gitlab.client import (
    GitLabClient,
    GitLabNoAuthStrategy,
    GitLabOAuthAuthStrategy,
)
from kepler_mcp_gitlab.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthenticationError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabValidationError,
)

__all__ = [
    "GitLabAPIError",
    "GitLabAuthenticationError",
    "GitLabClient",
    "GitLabNoAuthStrategy",
    "GitLabNotFoundError",
    "GitLabOAuthAuthStrategy",
    "GitLabRateLimitError",
    "GitLabValidationError",
]
