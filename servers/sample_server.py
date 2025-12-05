#!/usr/bin/env python3
"""Sample MCP server demonstrating template usage.

This script shows how to use the kepler_mcp_gitlab template to create
a custom MCP server. For real implementations, you would modify
the application.py file to register your own tools.
"""

from __future__ import annotations

import asyncio

from kepler_mcp_gitlab.config import load_config
from kepler_mcp_gitlab.logging_config import setup_logging
from kepler_mcp_gitlab.server import create_app
from kepler_mcp_gitlab.transport import run_stdio


async def main() -> None:
    """Run the sample MCP server."""
    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config)

    # Create MCP application
    app = create_app(config)

    # Run in stdio mode
    await run_stdio(app)


if __name__ == "__main__":
    asyncio.run(main())
