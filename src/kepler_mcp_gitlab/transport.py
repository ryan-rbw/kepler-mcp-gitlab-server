"""Transport adapters for MCP server.

Provides stdio and SSE transport implementations for different
client connection methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.security import generate_secure_token

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from starlette.requests import Request

    from kepler_mcp_gitlab.config import Config
    from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow
    from kepler_mcp_gitlab.oauth.session import PendingAuthState, SessionManager

logger = get_logger(__name__)


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
    routes: list[Route] = []

    # Health check endpoint
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "app_name": config.app_name,
            "environment": config.environment.value,
        })

    routes.append(Route("/health", health_check, methods=["GET"]))

    # SSE endpoint for MCP messages
    async def sse_endpoint(request: Request) -> Response:
        """SSE endpoint for MCP message streaming."""
        # Check authentication if OAuth is enabled
        if config.oauth_user_auth_enabled:
            session_id = request.cookies.get("session_id")
            if not session_id or session_manager is None:
                # Redirect to OAuth
                return RedirectResponse(url="/oauth/authorize", status_code=302)

            session = await session_manager.get_session(session_id)
            if session is None:
                return RedirectResponse(url="/oauth/authorize", status_code=302)

            # Store session in request state for tools to access
            request.state.session_id = session_id
            request.state.user_id = session.user_id

        # Delegate to FastMCP's SSE handling
        result: Response = await mcp_app.handle_sse(request)  # type: ignore[attr-defined]
        return result

    routes.append(Route(config.sse_path, sse_endpoint, methods=["GET"]))

    # Message endpoint for client-to-server messages
    async def message_endpoint(request: Request) -> Response:
        """HTTP endpoint for client-to-server MCP messages."""
        result: Response = await mcp_app.handle_message(request)  # type: ignore[attr-defined]
        return result

    routes.append(Route("/message", message_endpoint, methods=["POST"]))

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

                # Redirect to SSE endpoint with session cookie
                response = RedirectResponse(url=config.sse_path, status_code=302)
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
