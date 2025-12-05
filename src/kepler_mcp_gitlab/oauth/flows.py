"""OAuth 2.0 flow implementations.

Provides Authorization Code flow with PKCE for user authentication
and Client Credentials flow for service-to-service authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.oauth.pkce import PKCEPair, create_pkce_pair
from kepler_mcp_gitlab.security import OAuthError, redact

logger = get_logger(__name__)

# Default HTTP timeout for OAuth requests
DEFAULT_TIMEOUT = 30.0

# Buffer time before token expiry to trigger refresh
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


@dataclass
class TokenSet:
    """OAuth 2.0 token set.

    Contains access token, optional refresh token, and metadata.
    """

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if the token should be refreshed."""
        return datetime.now(UTC) >= (self.expires_at - TOKEN_REFRESH_BUFFER)

    @classmethod
    def from_token_response(
        cls,
        response: dict[str, Any],
        default_expires_in: int = 3600,
    ) -> TokenSet:
        """Create TokenSet from OAuth token response.

        Args:
            response: Token endpoint response
            default_expires_in: Default expiry if not in response

        Returns:
            TokenSet instance
        """
        expires_in = response.get("expires_in", default_expires_in)
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        return cls(
            access_token=response["access_token"],
            refresh_token=response.get("refresh_token"),
            expires_at=expires_at,
            token_type=response.get("token_type", "Bearer"),
            scope=response.get("scope"),
        )


class OAuth2AuthorizationCodeFlow:
    """OAuth 2.0 Authorization Code flow with PKCE.

    Implements the full authorization code flow for authenticating
    users via an external identity provider.
    """

    def __init__(
        self,
        authorization_url: str,
        token_url: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
        scope: str,
        userinfo_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the authorization code flow.

        Args:
            authorization_url: OAuth authorization endpoint
            token_url: OAuth token endpoint
            client_id: OAuth client identifier
            client_secret: OAuth client secret (optional for public clients)
            redirect_uri: Registered redirect/callback URI
            scope: Space-separated list of scopes
            userinfo_url: Optional userinfo endpoint
            http_client: Optional custom HTTP client
        """
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.userinfo_url = userinfo_url
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client if we own it."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def create_authorization_url(self, state: str) -> tuple[str, PKCEPair]:
        """Generate the authorization URL with PKCE parameters.

        Args:
            state: Random state parameter for CSRF protection

        Returns:
            Tuple of (authorization URL, PKCE pair for later verification)
        """
        pkce = create_pkce_pair()

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": pkce.code_challenge,
            "code_challenge_method": "S256",
        }

        url = f"{self.authorization_url}?{urlencode(params)}"
        logger.debug("Created authorization URL for client %s", self.client_id)

        return url, pkce

    async def exchange_code_for_tokens(
        self,
        code: str,
        pkce_verifier: str,
    ) -> TokenSet:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from callback
            pkce_verifier: PKCE code verifier from authorization request

        Returns:
            TokenSet with access and refresh tokens

        Raises:
            OAuthError: If token exchange fails
        """
        client = await self._get_client()

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": pkce_verifier,
        }

        # Include client secret if configured
        if self.client_secret:
            data["client_secret"] = self.client_secret

        logger.debug("Exchanging authorization code for tokens")

        try:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info(
                "Successfully exchanged code for tokens (scope: %s)",
                token_data.get("scope", "N/A"),
            )

            return TokenSet.from_token_response(token_data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(
                "Token exchange failed: %s %s - %s",
                e.response.status_code,
                e.response.reason_phrase,
                error_body,
            )
            raise OAuthError(f"Token exchange failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error("Token exchange error: %s", e)
            raise OAuthError(f"Token exchange error: {e}") from e

    async def refresh_access_token(self, refresh_token: str) -> TokenSet:
        """Use refresh token to obtain new access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New TokenSet with fresh access token

        Raises:
            OAuthError: If token refresh fails
        """
        client = await self._get_client()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        logger.debug("Refreshing access token")

        try:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

            # Preserve refresh token if not returned
            if "refresh_token" not in token_data:
                token_data["refresh_token"] = refresh_token

            logger.info("Successfully refreshed access token")

            return TokenSet.from_token_response(token_data)

        except httpx.HTTPStatusError as e:
            logger.error(
                "Token refresh failed: %s %s",
                e.response.status_code,
                e.response.reason_phrase,
            )
            raise OAuthError(f"Token refresh failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error("Token refresh error: %s", e)
            raise OAuthError(f"Token refresh error: {e}") from e

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch user profile from userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            User profile data

        Raises:
            OAuthError: If userinfo fetch fails or endpoint not configured
        """
        if not self.userinfo_url:
            raise OAuthError("Userinfo endpoint not configured")

        client = await self._get_client()

        logger.debug("Fetching user info")

        try:
            response = await client.get(
                self.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            user_data: dict[str, Any] = response.json()

            logger.debug(
                "Retrieved user info for: %s",
                user_data.get("email", user_data.get("username", "unknown")),
            )

            return user_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "Userinfo fetch failed: %s %s",
                e.response.status_code,
                e.response.reason_phrase,
            )
            raise OAuthError(f"Userinfo fetch failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error("Userinfo fetch error: %s", e)
            raise OAuthError(f"Userinfo fetch error: {e}") from e


class OAuth2ClientCredentialsFlow:
    """OAuth 2.0 Client Credentials flow.

    Used for service-to-service authentication where no user
    interaction is required.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize client credentials flow.

        Args:
            token_url: OAuth token endpoint
            client_id: OAuth client identifier
            client_secret: OAuth client secret
            scope: Optional space-separated scopes
            http_client: Optional custom HTTP client
        """
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._http_client = http_client
        self._owns_client = http_client is None
        self._cached_token: TokenSet | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client if we own it."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_access_token(self) -> TokenSet:
        """Obtain an access token using client credentials.

        Automatically caches and refreshes tokens.

        Returns:
            TokenSet with access token

        Raises:
            OAuthError: If token request fails
        """
        # Return cached token if still valid
        if self._cached_token and not self._cached_token.needs_refresh:
            return self._cached_token

        client = await self._get_client()

        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        if self.scope:
            data["scope"] = self.scope

        logger.debug(
            "Requesting client credentials token (client: %s, secret: %s)",
            self.client_id,
            redact(self.client_secret),
        )

        try:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

            self._cached_token = TokenSet.from_token_response(token_data)

            logger.info(
                "Successfully obtained client credentials token (expires: %s)",
                self._cached_token.expires_at.isoformat(),
            )

            return self._cached_token

        except httpx.HTTPStatusError as e:
            logger.error(
                "Client credentials request failed: %s %s",
                e.response.status_code,
                e.response.reason_phrase,
            )
            raise OAuthError(
                f"Client credentials request failed: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error("Client credentials request error: %s", e)
            raise OAuthError(f"Client credentials request error: {e}") from e

    def clear_cache(self) -> None:
        """Clear cached token."""
        self._cached_token = None
