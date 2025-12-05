"""Command-line interface for Kepler MCP Server.

Provides CLI commands for running the MCP server in different modes.
"""

from __future__ import annotations

import asyncio
import sys

import typer

from kepler_mcp_gitlab import __version__
from kepler_mcp_gitlab.config import Config, ConfigError, TransportMode, load_config
from kepler_mcp_gitlab.logging_config import get_logger, setup_logging

app = typer.Typer(
    name="kepler-mcp-gitlab",
    help="Kepler MCP Server - A production-ready MCP server template",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"kepler-mcp-gitlab version {__version__}")
        try:
            import fastmcp

            typer.echo(f"fastmcp version {fastmcp.__version__}")
        except (ImportError, AttributeError):
            typer.echo("fastmcp version unknown")

        import sys

        typer.echo(f"Python {sys.version}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Kepler MCP Server CLI."""


@app.command()
def serve(
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file (JSON or YAML)",
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="Host to bind to (SSE mode only)",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to bind to (SSE mode only)",
    ),
    transport: str | None = typer.Option(
        None,
        "--transport",
        "-t",
        help="Transport mode (stdio or sse)",
    ),
) -> None:
    """Run the MCP server.

    The server can run in two transport modes:
    - stdio: For local integrations (Claude Desktop, etc.)
    - sse: For HTTP-based integrations (ChatGPT custom connectors, etc.)
    """
    # Build CLI args dict
    cli_args: dict[str, str | int | None] = {}
    if log_level:
        cli_args["log_level"] = log_level
    if host:
        cli_args["host"] = host
    if port:
        cli_args["port"] = port
    if transport:
        cli_args["transport_mode"] = transport

    try:
        # Load configuration
        config = load_config(path=config_path, cli_args=cli_args)

        # Setup logging
        setup_logging(config)
        logger = get_logger(__name__)

        logger.info(
            "Starting Kepler MCP Server (app: %s, env: %s, transport: %s)",
            config.app_name,
            config.environment.value,
            config.transport_mode.value,
        )

        # Run the server
        asyncio.run(_run_server(config))

    except ConfigError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("Shutting down (keyboard interrupt)")
        raise typer.Exit(code=0) from None
    except Exception as e:
        typer.echo(f"Fatal error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _run_server(config: Config) -> None:
    """Run the MCP server with the configured transport.

    Args:
        config: Application configuration
    """
    from kepler_mcp_gitlab.server import create_app

    # Create the MCP application
    mcp_app = create_app(config)

    if config.transport_mode == TransportMode.STDIO:
        # Run in stdio mode
        from kepler_mcp_gitlab.transport import run_stdio

        await run_stdio(mcp_app)
    else:
        # Run in SSE mode
        from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow
        from kepler_mcp_gitlab.oauth.session import PendingAuthState, SessionManager
        from kepler_mcp_gitlab.oauth.token_store import create_token_store
        from kepler_mcp_gitlab.transport import create_sse_app, run_sse

        # Setup OAuth if enabled
        oauth_flow: OAuth2AuthorizationCodeFlow | None = None
        session_manager: SessionManager | None = None
        pending_auth_state: PendingAuthState | None = None

        if config.oauth_user_auth_enabled:
            # Create token store
            encryption_key = (
                config.token_encryption_key.get_secret_value()
                if config.token_encryption_key
                else None
            )
            token_store = create_token_store(
                encryption_key=encryption_key,
                file_path=config.token_store_path,
            )

            # Create OAuth flow
            oauth_flow = OAuth2AuthorizationCodeFlow(
                authorization_url=config.oauth_authorization_url or "",
                token_url=config.oauth_token_url or "",
                client_id=config.oauth_client_id or "",
                client_secret=(
                    config.oauth_client_secret.get_secret_value()
                    if config.oauth_client_secret
                    else None
                ),
                redirect_uri=config.oauth_redirect_uri or "",
                scope=config.oauth_scope or "",
                userinfo_url=config.oauth_userinfo_url,
            )

            # Create session manager
            session_manager = SessionManager(
                token_store=token_store,
                oauth_flow=oauth_flow,
            )

            # Create pending auth state manager
            pending_auth_state = PendingAuthState()

            logger = get_logger(__name__)
            logger.info("OAuth user authentication enabled")

        # Create SSE app
        sse_app = create_sse_app(
            mcp_app=mcp_app,
            config=config,
            oauth_flow=oauth_flow,
            session_manager=session_manager,
            pending_auth_state=pending_auth_state,
        )

        logger = get_logger(__name__)
        logger.info(
            "SSE server URL: http://%s:%d%s",
            config.host,
            config.port,
            config.sse_path,
        )

        await run_sse(sse_app, config.host, config.port)


@app.command()
def version() -> None:
    """Print version information."""
    typer.echo(f"kepler-mcp-gitlab version {__version__}")
    try:
        import fastmcp

        typer.echo(f"fastmcp version {fastmcp.__version__}")
    except (ImportError, AttributeError):
        typer.echo("fastmcp version unknown")

    typer.echo(f"Python {sys.version}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
