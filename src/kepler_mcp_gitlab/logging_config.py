"""Logging configuration for Kepler MCP Server.

Provides structured logging setup with configurable levels
and consistent formatting across the application.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kepler_mcp_gitlab.config import Config

# Package logger name
LOGGER_NAME = "kepler_mcp_gitlab"

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Track if logging has been set up to prevent duplicate handlers
_logging_configured = False


def setup_logging(config: Config) -> None:
    """Configure logging for the application.

    Sets up the root logger and package logger with the configured
    log level and format. This function is idempotent - calling it
    multiple times will not create duplicate handlers.

    Args:
        config: Application configuration containing log_level setting
    """
    global _logging_configured

    # Get the numeric log level
    log_level = getattr(logging, config.log_level.value)

    # Get or create the package logger
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level)

    # Prevent duplicate handler setup
    if _logging_configured:
        # Just update the level if already configured
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)
        return

    # Remove any existing handlers to prevent duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    _logging_configured = True

    logger.debug("Logging configured with level %s", config.log_level.value)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Returns a child logger of the package logger, ensuring
    consistent formatting and configuration.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured Logger instance
    """
    # If name starts with package name, use as-is
    if name.startswith(LOGGER_NAME):
        return logging.getLogger(name)

    # Otherwise, create as child of package logger
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def reset_logging() -> None:
    """Reset logging configuration.

    Used primarily for testing to allow re-initialization
    of the logging setup.
    """
    global _logging_configured
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    _logging_configured = False
