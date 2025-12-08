"""Transport adapters for MCP server.

Provides stdio and SSE transport implementations for different
client connection methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route

from kepler_mcp_gitlab.context import (
    register_transport_session,
    set_session_manager,
)
from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.security import generate_secure_token

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from starlette.requests import Request
    from starlette.types import ASGIApp, Receive, Scope, Send

    from kepler_mcp_gitlab.config import Config
    from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow
    from kepler_mcp_gitlab.oauth.session import PendingAuthState, SessionManager

logger = get_logger(__name__)


class OAuthSessionMiddleware:
    """ASGI middleware to capture OAuth session from cookies and link to MCP transport.

    This middleware intercepts requests to the /messages endpoint and extracts
    the MCP transport session ID from the query params, then links it to the
    OAuth session from the cookie set during initial SSE connection.
    """

    def __init__(self, app: ASGIApp, session_manager: SessionManager | None) -> None:
        self.app = app
        self.session_manager = session_manager
        # Track SSE connections: MCP transport session -> OAuth session
        self._pending_sse_sessions: dict[str, str] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # For SSE endpoint, capture the OAuth session cookie
        if path == "/sse":
            oauth_session_id = self._get_cookie(scope, "session_id")
            if oauth_session_id:
                # Store temporarily - we'll link it when we see the session ID
                # The SSE response will contain the transport session ID
                scope["state"] = scope.get("state", {})
                scope["state"]["oauth_session_id"] = oauth_session_id
                logger.debug("SSE connection with OAuth session: %s", oauth_session_id[:8])

            # Wrap send to capture the transport session ID from SSE events
            original_send = send

            async def capturing_send(message: Any) -> None:
                if message.get("type") == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        body_str = body.decode("utf-8", errors="ignore")
                        # Look for: data: /messages/?session_id=xxx
                        if "session_id=" in body_str and oauth_session_id:
                            import re

                            match = re.search(r"session_id=([a-f0-9]+)", body_str)
                            if match:
                                transport_session_id = match.group(1)
                                register_transport_session(
                                    transport_session_id, oauth_session_id
                                )
                await original_send(message)

            await self.app(scope, receive, capturing_send)
            return

        await self.app(scope, receive, send)

    def _get_cookie(self, scope: Scope, name: str) -> str | None:
        """Extract a cookie value from ASGI scope headers."""
        headers: list[tuple[bytes, bytes]] = cast(
            "list[tuple[bytes, bytes]]", scope.get("headers", [])
        )
        for header_name, header_value in headers:
            if header_name == b"cookie":
                cookies_str = header_value.decode("utf-8", errors="ignore")
                for raw_cookie in cookies_str.split(";"):
                    cookie_pair = raw_cookie.strip()
                    if cookie_pair.startswith(f"{name}="):
                        return cookie_pair[len(name) + 1 :]
        return None


async def run_stdio(app: FastMCP) -> None:
    """Run the MCP server using stdio transport.

    Reads JSON-RPC messages from stdin and writes responses to stdout.
    This is the default mode for local integrations like Claude Desktop.

    Args:
        app: FastMCP application instance
    """
    logger.info("Starting MCP server in stdio mode")
    await app.run_stdio_async()


def create_sse_app(
    mcp_app: FastMCP,
    config: Config,
    oauth_flow: OAuth2AuthorizationCodeFlow | None = None,
    session_manager: SessionManager | None = None,
    pending_auth_state: PendingAuthState | None = None,
) -> Starlette:
    """Create a Starlette ASGI application for SSE transport.

    Includes OAuth endpoints if oauth_user_auth_enabled is True.

    Args:
        mcp_app: FastMCP application instance
        config: Application configuration
        oauth_flow: OAuth flow for user authentication
        session_manager: Session manager for authenticated sessions
        pending_auth_state: Manager for pending OAuth states

    Returns:
        Configured Starlette application
    """
    # Set global session manager for OAuth authentication
    if session_manager is not None:
        set_session_manager(session_manager)

    routes: list[Route | Mount] = []

    # Health check endpoint
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "app_name": config.app_name,
            "environment": config.environment.value,
        })

    routes.append(Route("/health", health_check, methods=["GET"]))

    # OAuth endpoints (if enabled)
    if config.oauth_user_auth_enabled and oauth_flow and pending_auth_state:

        async def oauth_authorize(request: Request) -> RedirectResponse:
            """Initiate OAuth authorization flow."""
            state = generate_secure_token(32)
            auth_url, pkce = oauth_flow.create_authorization_url(state)

            # Store PKCE verifier for later
            await pending_auth_state.create_state(state, pkce.code_verifier)

            logger.debug("Initiating OAuth flow with state %s", state[:8])
            return RedirectResponse(url=auth_url, status_code=302)

        async def oauth_callback(request: Request) -> Response:
            """Handle OAuth callback."""
            code = request.query_params.get("code")
            state = request.query_params.get("state")
            error = request.query_params.get("error")

            if error:
                error_description = request.query_params.get(
                    "error_description", "Unknown error"
                )
                logger.error("OAuth error: %s - %s", error, error_description)
                return JSONResponse(
                    {"error": error, "description": error_description},
                    status_code=400,
                )

            if not code or not state:
                return JSONResponse(
                    {"error": "Missing code or state parameter"},
                    status_code=400,
                )

            # Verify state and get PKCE verifier
            pkce_verifier = await pending_auth_state.consume_state(state)
            if pkce_verifier is None:
                logger.warning("Invalid or expired OAuth state: %s", state[:8])
                return JSONResponse(
                    {"error": "Invalid or expired state"},
                    status_code=400,
                )

            try:
                # Exchange code for tokens
                tokens = await oauth_flow.exchange_code_for_tokens(code, pkce_verifier)

                # Get user info if endpoint is configured
                user_id: str
                if oauth_flow.userinfo_url:
                    user_info = await oauth_flow.get_user_info(tokens.access_token)
                    user_id = str(
                        user_info.get("id")
                        or user_info.get("sub")
                        or user_info.get("email")
                        or "unknown"
                    )
                else:
                    user_id = generate_secure_token(16)

                # Create session
                if session_manager is None:
                    return JSONResponse(
                        {"error": "Session manager not configured"},
                        status_code=500,
                    )

                session_id = await session_manager.create_session(user_id, tokens)

                # Redirect to a success page with session cookie
                # (SSE connection will be initiated by the MCP client)
                response_data = {
                    "status": "authenticated",
                    "message": "OAuth authentication successful. You can now use the MCP server.",
                    "sse_endpoint": config.sse_path,
                }
                # Include session_id in response body for local development testing
                if config.environment.value == "local":
                    response_data["session_id"] = session_id
                response = JSONResponse(response_data)
                response.set_cookie(
                    key="session_id",
                    value=session_id,
                    httponly=True,
                    secure=config.environment.value != "local",
                    samesite="lax",
                    max_age=86400,  # 24 hours
                )

                logger.info("OAuth flow completed for user %s", user_id)
                return response

            except Exception as e:
                logger.error("OAuth callback error: %s", e)
                return JSONResponse(
                    {"error": "Authentication failed"},
                    status_code=500,
                )

        routes.append(Route("/oauth/authorize", oauth_authorize, methods=["GET"]))
        routes.append(Route("/oauth/callback", oauth_callback, methods=["GET"]))

    # Get FastMCP's HTTP app configured for SSE transport and mount it
    # FastMCP handles the SSE endpoint at the configured path
    base_http_app = mcp_app.http_app(path=config.sse_path, transport="sse")

    # Wrap with OAuth session middleware to link MCP transport sessions to OAuth sessions
    if config.oauth_user_auth_enabled and session_manager is not None:
        fastmcp_http_app: ASGIApp = OAuthSessionMiddleware(base_http_app, session_manager)
    else:
        fastmcp_http_app = base_http_app

    routes.append(Mount("/", app=fastmcp_http_app))

    # CORS middleware for cross-origin requests
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    return Starlette(routes=routes, middleware=middleware)


async def run_sse(app: Starlette, host: str, port: int) -> None:
    """Run the SSE server using uvicorn.

    Args:
        app: Starlette ASGI application
        host: Host to bind to
        port: Port to bind to
    """
    import uvicorn

    logger.info("Starting MCP server in SSE mode on %s:%d", host, port)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()
