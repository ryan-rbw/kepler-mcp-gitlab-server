"""Security utilities for Kepler MCP Server.

Provides secret handling, token redaction, authentication strategies,
and helper functions for secure operations.
"""

from __future__ import annotations

import hmac
import secrets
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from kepler_mcp_gitlab.logging_config import get_logger

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config
    from kepler_mcp_gitlab.oauth.flows import OAuth2ClientCredentialsFlow
    from kepler_mcp_gitlab.oauth.session import SessionManager

logger = get_logger(__name__)


class OAuthError(Exception):
    """Raised when an OAuth operation fails."""


def redact(value: str | None) -> str:
    """Redact a potentially sensitive value for safe logging.

    Args:
        value: The value to redact

    Returns:
        "***" if value is non-empty, "<empty>" if empty/None
    """
    if value is None or value == "":
        return "<empty>"
    return "***"


def constant_time_equals(a: str | None, b: str | None) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string to compare
        b: Second string to compare

    Returns:
        True if strings are equal, False otherwise
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return hmac.compare_digest(a.encode(), b.encode())


def validate_shared_token(expected: str | None, provided: str | None) -> bool:
    """Validate a shared bearer token.

    If expected token is empty/None, validation passes only if
    provided is also empty. Otherwise, uses constant-time comparison.

    Args:
        expected: The expected token value
        provided: The token value provided by the client

    Returns:
        True if validation passes, False otherwise
    """
    if not expected:
        return not provided

    return constant_time_equals(expected, provided)


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        nbytes: Number of random bytes (default 32 = 256 bits)

    Returns:
        URL-safe base64-encoded token string
    """
    return secrets.token_urlsafe(nbytes)


class AuthStrategy(ABC):
    """Abstract base class for authentication strategies.

    Authentication strategies provide a consistent interface for
    obtaining authorization headers for API calls.
    """

    @abstractmethod
    async def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers for an API request.

        Returns:
            Dictionary of headers to include in the request
        """


class NoAuthStrategy(AuthStrategy):
    """Authentication strategy that provides no authentication."""

    async def get_auth_headers(self) -> dict[str, str]:
        """Return empty headers."""
        return {}


class StaticTokenAuthStrategy(AuthStrategy):
    """Authentication strategy using a static token.

    Suitable for personal access tokens or API keys.
    """

    def __init__(self, header_name: str, token_value: str) -> None:
        """Initialize with header name and token value.

        Args:
            header_name: Name of the header (e.g., "Authorization")
            token_value: Token value (e.g., "Bearer abc123")
        """
        self._header_name = header_name
        self._token_value = token_value

    async def get_auth_headers(self) -> dict[str, str]:
        """Return the static token header."""
        return {self._header_name: self._token_value}


class SessionAuthStrategy(AuthStrategy):
    """Authentication strategy using session-based OAuth tokens.

    Delegates to SessionManager to get valid tokens, which handles
    automatic token refresh.
    """

    def __init__(self, session_manager: SessionManager, session_id: str) -> None:
        """Initialize with session manager and session ID.

        Args:
            session_manager: SessionManager instance
            session_id: ID of the authenticated session
        """
        self._session_manager = session_manager
        self._session_id = session_id

    async def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers from the session.

        Returns:
            Authorization headers with current valid token

        Raises:
            OAuthError: If session is invalid or token refresh fails
        """
        try:
            return await self._session_manager.get_auth_headers_for_session(self._session_id)
        except Exception as e:
            logger.error("Failed to get auth headers for session %s: %s", self._session_id, e)
            raise OAuthError(f"Failed to get authorization: {e}") from e


class ServiceCredentialsAuthStrategy(AuthStrategy):
    """Authentication strategy using OAuth client credentials flow.

    Used for service-to-service authentication.
    """

    def __init__(self, flow: OAuth2ClientCredentialsFlow) -> None:
        """Initialize with client credentials flow.

        Args:
            flow: Configured OAuth2ClientCredentialsFlow instance
        """
        self._flow = flow

    async def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers using client credentials.

        Returns:
            Authorization headers with access token

        Raises:
            OAuthError: If token request fails
        """
        try:
            token_set = await self._flow.get_access_token()
            return {"Authorization": f"{token_set.token_type} {token_set.access_token}"}
        except Exception as e:
            logger.error("Failed to get service credentials token: %s", e)
            raise OAuthError(f"Failed to get service token: {e}") from e


def build_auth_strategy(
    config: Config,
    session_manager: SessionManager | None = None,
    session_id: str | None = None,
    client_credentials_flow: OAuth2ClientCredentialsFlow | None = None,
) -> AuthStrategy:
    """Build an appropriate AuthStrategy based on configuration.

    Priority:
    1. If oauth_user_auth_enabled and session_id provided, use SessionAuthStrategy
    2. If oauth_service_auth_enabled and flow provided, use ServiceCredentialsAuthStrategy
    3. If auth_token is set, use StaticTokenAuthStrategy
    4. Otherwise, return NoAuthStrategy

    Args:
        config: Application configuration
        session_manager: Optional SessionManager for user auth
        session_id: Optional session ID for user auth
        client_credentials_flow: Optional OAuth flow for service auth

    Returns:
        Configured AuthStrategy instance
    """
    # User OAuth authentication
    if config.oauth_user_auth_enabled and session_manager and session_id:
        logger.debug("Using SessionAuthStrategy for session %s", session_id)
        return SessionAuthStrategy(session_manager, session_id)

    # Service OAuth authentication
    if config.oauth_service_auth_enabled and client_credentials_flow:
        logger.debug("Using ServiceCredentialsAuthStrategy")
        return ServiceCredentialsAuthStrategy(client_credentials_flow)

    # Static token authentication
    if config.auth_token:
        logger.debug("Using StaticTokenAuthStrategy")
        return StaticTokenAuthStrategy(
            "Authorization",
            f"Bearer {config.auth_token.get_secret_value()}",
        )

    # No authentication
    logger.debug("Using NoAuthStrategy")
    return NoAuthStrategy()


def mask_sensitive_data(
    data: dict[str, Any], sensitive_keys: set[str] | None = None
) -> dict[str, Any]:
    """Mask sensitive data in a dictionary for logging.

    Args:
        data: Dictionary potentially containing sensitive data
        sensitive_keys: Set of keys to mask (uses defaults if not provided)

    Returns:
        Copy of dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "access_token",
            "refresh_token",
            "token",
            "secret",
            "password",
            "client_secret",
            "authorization",
            "auth_token",
        }

    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = mask_sensitive_data(value, sensitive_keys)
        elif any(sensitive in key.lower() for sensitive in sensitive_keys):
            result[key] = "***"
        else:
            result[key] = value

    return result
