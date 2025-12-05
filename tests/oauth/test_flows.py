"""Tests for OAuth flow implementations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from kepler_mcp_gitlab.oauth.flows import (
    OAuth2AuthorizationCodeFlow,
    OAuth2ClientCredentialsFlow,
    TokenSet,
)
from kepler_mcp_gitlab.security import OAuthError


class TestTokenSet:
    """Tests for TokenSet dataclass."""

    def test_from_token_response(self) -> None:
        """Test creating TokenSet from response."""
        response = {
            "access_token": "access123",
            "refresh_token": "refresh123",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "read write",
        }

        token_set = TokenSet.from_token_response(response)

        assert token_set.access_token == "access123"
        assert token_set.refresh_token == "refresh123"
        assert token_set.token_type == "Bearer"
        assert token_set.scope == "read write"

    def test_is_expired(self) -> None:
        """Test expiration check."""
        # Expired token
        expired = TokenSet(
            access_token="token",
            refresh_token=None,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert expired.is_expired is True

        # Valid token
        valid = TokenSet(
            access_token="token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert valid.is_expired is False

    def test_needs_refresh(self) -> None:
        """Test refresh need check."""
        # Token expiring soon
        expiring_soon = TokenSet(
            access_token="token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(minutes=2),
        )
        assert expiring_soon.needs_refresh is True

        # Token with plenty of time
        plenty_time = TokenSet(
            access_token="token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert plenty_time.needs_refresh is False


class TestOAuth2AuthorizationCodeFlow:
    """Tests for OAuth2AuthorizationCodeFlow class."""

    def test_create_authorization_url(self) -> None:
        """Test authorization URL generation."""
        flow = OAuth2AuthorizationCodeFlow(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
            scope="read write",
        )

        url, pkce = flow.create_authorization_url("test-state")

        assert "https://auth.example.com/authorize" in url
        assert "client_id=test-client" in url
        assert "state=test-state" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert pkce.code_verifier is not None
        assert pkce.code_challenge is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self) -> None:
        """Test token exchange."""
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "access123",
                    "refresh_token": "refresh123",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )

        flow = OAuth2AuthorizationCodeFlow(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
            scope="read write",
        )

        tokens = await flow.exchange_code_for_tokens("auth-code", "pkce-verifier")

        assert tokens.access_token == "access123"
        assert tokens.refresh_token == "refresh123"

        await flow.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self) -> None:
        """Test token exchange failure."""
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(400, json={"error": "invalid_grant"})
        )

        flow = OAuth2AuthorizationCodeFlow(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
            scope="read write",
        )

        with pytest.raises(OAuthError, match="Token exchange failed"):
            await flow.exchange_code_for_tokens("auth-code", "pkce-verifier")

        await flow.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_refresh_access_token(self) -> None:
        """Test token refresh."""
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "new-access",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )

        flow = OAuth2AuthorizationCodeFlow(
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
            scope="read write",
        )

        tokens = await flow.refresh_access_token("refresh-token")

        assert tokens.access_token == "new-access"
        assert tokens.refresh_token == "refresh-token"  # Preserved

        await flow.close()


class TestOAuth2ClientCredentialsFlow:
    """Tests for OAuth2ClientCredentialsFlow class."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_access_token(self) -> None:
        """Test getting access token."""
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "service-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )

        flow = OAuth2ClientCredentialsFlow(
            token_url="https://auth.example.com/token",
            client_id="service-client",
            client_secret="service-secret",
            scope="api",
        )

        tokens = await flow.get_access_token()

        assert tokens.access_token == "service-token"
        assert tokens.token_type == "Bearer"

        await flow.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_caches_token(self) -> None:
        """Test that token is cached."""
        call_count = 0

        def mock_response(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"token-{call_count}",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )

        respx.post("https://auth.example.com/token").mock(side_effect=mock_response)

        flow = OAuth2ClientCredentialsFlow(
            token_url="https://auth.example.com/token",
            client_id="service-client",
            client_secret="service-secret",
        )

        # Multiple calls should use cached token
        token1 = await flow.get_access_token()
        token2 = await flow.get_access_token()

        assert token1.access_token == token2.access_token
        assert call_count == 1  # Only one HTTP call

        await flow.close()
