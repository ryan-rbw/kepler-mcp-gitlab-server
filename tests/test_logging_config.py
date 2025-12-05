"""Tests for logging configuration module."""

from __future__ import annotations

import logging

import pytest

from kepler_mcp_gitlab.config import Config, LogLevel
from kepler_mcp_gitlab.logging_config import (
    LOGGER_NAME,
    get_logger,
    reset_logging,
    setup_logging,
)


class TestLoggingSetup:
    """Tests for logging setup."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self) -> None:
        """Reset logging state before each test."""
        reset_logging()

    def test_setup_logging_creates_handler(self) -> None:
        """Test that setup_logging creates a handler."""
        config = Config(log_level=LogLevel.DEBUG)
        setup_logging(config)

        logger = logging.getLogger(LOGGER_NAME)
        assert len(logger.handlers) == 1
        assert logger.level == logging.DEBUG

    def test_setup_logging_idempotent(self) -> None:
        """Test that setup_logging is idempotent."""
        config = Config(log_level=LogLevel.DEBUG)

        setup_logging(config)
        setup_logging(config)
        setup_logging(config)

        logger = logging.getLogger(LOGGER_NAME)
        assert len(logger.handlers) == 1

    def test_setup_logging_updates_level(self) -> None:
        """Test that setup_logging updates level on subsequent calls."""
        config_debug = Config(log_level=LogLevel.DEBUG)
        config_info = Config(log_level=LogLevel.INFO)

        setup_logging(config_debug)
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.DEBUG

        setup_logging(config_info)
        assert logger.level == logging.INFO


class TestGetLogger:
    """Tests for get_logger function."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self) -> None:
        """Reset logging state before each test."""
        reset_logging()

    def test_get_logger_returns_child_logger(self) -> None:
        """Test that get_logger returns a child logger."""
        logger = get_logger("test_module")
        assert logger.name == f"{LOGGER_NAME}.test_module"

    def test_get_logger_with_package_name(self) -> None:
        """Test that get_logger handles full package name."""
        logger = get_logger(f"{LOGGER_NAME}.submodule")
        assert logger.name == f"{LOGGER_NAME}.submodule"

    def test_get_logger_consistent(self) -> None:
        """Test that get_logger returns same logger for same name."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2
