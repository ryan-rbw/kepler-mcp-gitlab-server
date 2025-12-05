"""Tests for transport module."""

from __future__ import annotations

from starlette.testclient import TestClient

from kepler_mcp_gitlab.config import Config, TransportMode
from kepler_mcp_gitlab.server import create_app
from kepler_mcp_gitlab.transport import create_sse_app


class TestCreateSSEApp:
    """Tests for create_sse_app function."""

    def test_creates_starlette_app(self, default_config: Config) -> None:
        """Test that SSE app is created."""
        mcp_app = create_app(default_config)
        sse_config = Config(transport_mode=TransportMode.SSE)
        sse_app = create_sse_app(mcp_app, sse_config)

        assert sse_app is not None

    def test_health_endpoint(self, default_config: Config) -> None:
        """Test health endpoint responds correctly."""
        mcp_app = create_app(default_config)
        sse_config = Config(transport_mode=TransportMode.SSE)
        sse_app = create_sse_app(mcp_app, sse_config)

        client = TestClient(sse_app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == sse_config.app_name

    def test_cors_headers(self, default_config: Config) -> None:
        """Test CORS headers are present."""
        mcp_app = create_app(default_config)
        sse_config = Config(transport_mode=TransportMode.SSE)
        sse_app = create_sse_app(mcp_app, sse_config)

        client = TestClient(sse_app)
        response = client.options(
            "/health",
            headers={"Origin": "http://example.com"},
        )

        assert "access-control-allow-origin" in response.headers


class TestOAuthEndpoints:
    """Tests for OAuth endpoints in SSE transport."""

    def test_oauth_endpoints_not_present_when_disabled(
        self, default_config: Config
    ) -> None:
        """Test OAuth endpoints are not present when disabled."""
        mcp_app = create_app(default_config)
        sse_config = Config(
            transport_mode=TransportMode.SSE,
            oauth_user_auth_enabled=False,
        )
        sse_app = create_sse_app(mcp_app, sse_config)

        client = TestClient(sse_app)

        # OAuth endpoints should not exist
        response = client.get("/oauth/authorize", follow_redirects=False)
        assert response.status_code == 404

    def test_oauth_authorize_requires_config(self, oauth_config: Config) -> None:
        """Test OAuth authorize endpoint requires proper config."""
        from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow
        from kepler_mcp_gitlab.oauth.session import PendingAuthState, SessionManager
        from kepler_mcp_gitlab.oauth.token_store import InMemoryTokenStore

        mcp_app = create_app(oauth_config)

        # Create OAuth components
        oauth_flow = OAuth2AuthorizationCodeFlow(
            authorization_url=oauth_config.oauth_authorization_url or "",
            token_url=oauth_config.oauth_token_url or "",
            client_id=oauth_config.oauth_client_id or "",
            client_secret=None,
            redirect_uri=oauth_config.oauth_redirect_uri or "",
            scope=oauth_config.oauth_scope or "",
        )
        token_store = InMemoryTokenStore()
        session_manager = SessionManager(token_store)
        pending_state = PendingAuthState()

        sse_app = create_sse_app(
            mcp_app,
            oauth_config,
            oauth_flow=oauth_flow,
            session_manager=session_manager,
            pending_auth_state=pending_state,
        )

        client = TestClient(sse_app)

        # OAuth authorize should redirect to IdP
        response = client.get("/oauth/authorize", follow_redirects=False)
        assert response.status_code == 302
        assert oauth_config.oauth_authorization_url in response.headers["location"]
