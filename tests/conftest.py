"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest

from kepler_mcp_gitlab.config import Config, Environment, LogLevel, TransportMode


@pytest.fixture
def default_config() -> Config:
    """Create a default configuration for testing."""
    return Config()


@pytest.fixture
def dev_config() -> Config:
    """Create a development configuration for testing."""
    return Config(
        app_name="Test MCP Server",
        log_level=LogLevel.DEBUG,
        environment=Environment.DEV,
        transport_mode=TransportMode.SSE,
        host="127.0.0.1",
        port=8080,
    )


@pytest.fixture
def oauth_config() -> Config:
    """Create a configuration with OAuth enabled for testing."""
    return Config(
        app_name="OAuth Test Server",
        oauth_user_auth_enabled=True,
        oauth_authorization_url="https://auth.example.com/authorize",
        oauth_token_url="https://auth.example.com/token",
        oauth_client_id="test-client-id",
        oauth_client_secret="test-client-secret",
        oauth_redirect_uri="http://localhost:8000/oauth/callback",
        oauth_scope="read write",
        transport_mode=TransportMode.SSE,
    )


@pytest.fixture
def gitlab_config() -> Config:
    """Create a configuration with GitLab settings for testing."""
    return Config(
        app_name="GitLab Test Server",
        gitlab_url="https://gitlab.example.com",
        gitlab_token="glpat-test-token",
        gitlab_default_project_id="test-group/test-project",
    )
