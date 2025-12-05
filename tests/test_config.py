"""Tests for configuration module."""

from __future__ import annotations

import pytest

from kepler_mcp_gitlab.config import (
    Config,
    ConfigError,
    Environment,
    LogLevel,
    TransportMode,
    load_config,
)


class TestConfig:
    """Tests for Config model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = Config()

        assert config.app_name == "Kepler MCP Server"
        assert config.log_level == LogLevel.INFO
        assert config.environment == Environment.LOCAL
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.transport_mode == TransportMode.STDIO
        assert config.enable_metrics is False
        assert config.oauth_user_auth_enabled is False
        assert config.oauth_service_auth_enabled is False

    def test_custom_values(self) -> None:
        """Test configuration with custom values."""
        config = Config(
            app_name="Custom Server",
            log_level=LogLevel.DEBUG,
            environment=Environment.PROD,
            port=9000,
        )

        assert config.app_name == "Custom Server"
        assert config.log_level == LogLevel.DEBUG
        assert config.environment == Environment.PROD
        assert config.port == 9000

    def test_log_level_normalization(self) -> None:
        """Test that log level strings are normalized to uppercase."""
        config = Config(log_level="debug")  # type: ignore[arg-type]
        assert config.log_level == LogLevel.DEBUG

    def test_environment_normalization(self) -> None:
        """Test that environment strings are normalized to lowercase."""
        config = Config(environment="PROD")  # type: ignore[arg-type]
        assert config.environment == Environment.PROD

    def test_transport_mode_normalization(self) -> None:
        """Test that transport mode strings are normalized."""
        config = Config(transport_mode="SSE")  # type: ignore[arg-type]
        assert config.transport_mode == TransportMode.SSE

    def test_port_validation(self) -> None:
        """Test port number validation."""
        # Valid port
        config = Config(port=8080)
        assert config.port == 8080

        # Invalid port (too low)
        with pytest.raises(ValueError):
            Config(port=0)

        # Invalid port (too high)
        with pytest.raises(ValueError):
            Config(port=70000)


class TestOAuthValidation:
    """Tests for OAuth configuration validation."""

    def test_oauth_user_auth_requires_fields(self) -> None:
        """Test that OAuth user auth requires all fields."""
        with pytest.raises(ValueError, match="missing required fields"):
            Config(oauth_user_auth_enabled=True)

    def test_oauth_user_auth_valid(self) -> None:
        """Test valid OAuth user auth configuration."""
        config = Config(
            oauth_user_auth_enabled=True,
            oauth_authorization_url="https://auth.example.com/authorize",
            oauth_token_url="https://auth.example.com/token",
            oauth_client_id="client-id",
            oauth_redirect_uri="http://localhost:8000/callback",
            oauth_scope="read",
        )
        assert config.oauth_user_auth_enabled is True

    def test_oauth_service_auth_requires_fields(self) -> None:
        """Test that OAuth service auth requires all fields."""
        with pytest.raises(ValueError, match="missing required fields"):
            Config(oauth_service_auth_enabled=True)

    def test_oauth_service_auth_valid(self) -> None:
        """Test valid OAuth service auth configuration."""
        config = Config(
            oauth_service_auth_enabled=True,
            oauth_service_client_id="client-id",
            oauth_service_client_secret="client-secret",
            oauth_service_token_url="https://auth.example.com/token",
        )
        assert config.oauth_service_auth_enabled is True

    def test_token_store_requires_encryption_key(self) -> None:
        """Test that token store path requires encryption key."""
        with pytest.raises(ValueError, match="token_encryption_key is required"):
            Config(token_store_path="/path/to/tokens.enc")

    def test_token_store_with_encryption_key(self) -> None:
        """Test valid token store configuration."""
        config = Config(
            token_store_path="/path/to/tokens.enc",
            token_encryption_key="test-key",
        )
        assert config.token_store_path == "/path/to/tokens.enc"


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_config_defaults(self) -> None:
        """Test loading configuration with defaults."""
        config = load_config()
        assert config.app_name == "Kepler MCP Server"

    def test_load_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("KEPLER_MCP_APP_NAME", "Env Server")
        monkeypatch.setenv("KEPLER_MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("KEPLER_MCP_PORT", "9000")

        config = load_config()

        assert config.app_name == "Env Server"
        assert config.log_level == LogLevel.DEBUG
        assert config.port == 9000

    def test_load_config_cli_args_override_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that CLI args override environment variables."""
        monkeypatch.setenv("KEPLER_MCP_APP_NAME", "Env Server")

        config = load_config(cli_args={"app_name": "CLI Server"})

        assert config.app_name == "CLI Server"

    def test_load_config_invalid_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid configuration raises ConfigError."""
        monkeypatch.setenv("KEPLER_MCP_PORT", "invalid")

        with pytest.raises(ConfigError):
            load_config()
