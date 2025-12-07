"""Configuration management for Kepler MCP Server.

Provides configuration loading from environment variables, .env files,
and optional configuration files with proper precedence handling.
"""

from __future__ import annotations

import contextlib
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration validation fails."""


class LogLevel(str, Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Deployment environments."""

    LOCAL = "local"
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class TransportMode(str, Enum):
    """MCP transport modes."""

    STDIO = "stdio"
    SSE = "sse"


class Config(BaseModel):
    """Main configuration model for Kepler MCP Server.

    Configuration can be loaded from:
    - Environment variables with KEPLER_MCP_ prefix
    - Optional .env file in project root
    - Optional configuration file passed via CLI
    """

    # Core settings
    app_name: str = Field(default="Kepler MCP Server", description="Application name")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    environment: Environment = Field(
        default=Environment.LOCAL, description="Deployment environment"
    )

    # Server settings
    # S104/B104: Binding to 0.0.0.0 is intentional for Docker container networking.
    # In production, this should be behind a reverse proxy or firewall.
    host: str = Field(default="0.0.0.0", description="Server bind host")  # noqa: S104  # nosec B104
    port: int = Field(default=8000, ge=1, le=65535, description="Server bind port")
    enable_metrics: bool = Field(default=False, description="Enable metrics collection")

    # Transport settings
    transport_mode: TransportMode = Field(
        default=TransportMode.STDIO, description="MCP transport mode"
    )
    sse_path: str = Field(default="/sse", description="SSE endpoint path")

    # Simple auth token (used when oauth_user_auth_enabled is False)
    auth_token: SecretStr | None = Field(
        default=None, description="Simple bearer token for authentication"
    )

    # OAuth 2.0 User Authentication (Authorization Code with PKCE)
    oauth_user_auth_enabled: bool = Field(
        default=False, description="Enable OAuth user authentication"
    )
    oauth_authorization_url: str | None = Field(
        default=None, description="OAuth authorization endpoint URL"
    )
    oauth_token_url: str | None = Field(default=None, description="OAuth token endpoint URL")
    oauth_client_id: str | None = Field(default=None, description="OAuth client identifier")
    oauth_client_secret: SecretStr | None = Field(
        default=None, description="OAuth client secret"
    )
    oauth_scope: str | None = Field(
        default=None, description="OAuth scopes (space-separated)"
    )
    oauth_redirect_uri: str | None = Field(
        default=None, description="OAuth callback/redirect URI"
    )
    oauth_userinfo_url: str | None = Field(
        default=None, description="OAuth userinfo endpoint URL"
    )

    # OAuth 2.0 Service Authentication (Client Credentials)
    oauth_service_auth_enabled: bool = Field(
        default=False, description="Enable OAuth service-to-service authentication"
    )
    oauth_service_client_id: str | None = Field(
        default=None, description="Service OAuth client identifier"
    )
    oauth_service_client_secret: SecretStr | None = Field(
        default=None, description="Service OAuth client secret"
    )
    oauth_service_token_url: str | None = Field(
        default=None, description="Service OAuth token endpoint URL"
    )
    oauth_service_scope: str | None = Field(
        default=None, description="Service OAuth scopes"
    )

    # Token storage and encryption
    token_encryption_key: SecretStr | None = Field(
        default=None, description="Fernet encryption key for token storage"
    )
    token_store_path: str | None = Field(
        default=None, description="Path for persistent token storage"
    )

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(
        default=60, ge=1, description="Max requests per minute per session"
    )
    rate_limit_burst: int = Field(default=10, ge=1, description="Rate limit burst size")

    # GitLab settings
    gitlab_url: str = Field(
        default="https://gitlab.com", description="GitLab instance base URL"
    )

    model_config = {
        "extra": "allow",  # Allow extra fields for application-specific config
        "validate_assignment": True,
    }

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: Any) -> Any:
        """Normalize log level to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, v: Any) -> Any:
        """Normalize environment to lowercase."""
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("transport_mode", mode="before")
    @classmethod
    def normalize_transport_mode(cls, v: Any) -> Any:
        """Normalize transport mode to lowercase."""
        if isinstance(v, str):
            return v.lower()
        return v

    @model_validator(mode="after")
    def validate_oauth_user_auth(self) -> Config:
        """Validate OAuth user authentication configuration."""
        if self.oauth_user_auth_enabled:
            required_fields = [
                ("oauth_authorization_url", self.oauth_authorization_url),
                ("oauth_token_url", self.oauth_token_url),
                ("oauth_client_id", self.oauth_client_id),
                ("oauth_redirect_uri", self.oauth_redirect_uri),
                ("oauth_scope", self.oauth_scope),
            ]
            missing = [name for name, value in required_fields if not value]
            if missing:
                msg = (
                    f"OAuth user authentication is enabled but missing required fields: "
                    f"{', '.join(missing)}"
                )
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_oauth_service_auth(self) -> Config:
        """Validate OAuth service authentication configuration."""
        if self.oauth_service_auth_enabled:
            required_fields = [
                ("oauth_service_client_id", self.oauth_service_client_id),
                ("oauth_service_client_secret", self.oauth_service_client_secret),
                ("oauth_service_token_url", self.oauth_service_token_url),
            ]
            missing = [name for name, value in required_fields if not value]
            if missing:
                msg = (
                    f"OAuth service authentication is enabled but missing required fields: "
                    f"{', '.join(missing)}"
                )
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_token_store(self) -> Config:
        """Validate token store configuration."""
        if self.token_store_path and not self.token_encryption_key:
            msg = "token_encryption_key is required when token_store_path is set"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_sse_transport(self) -> Config:
        """Validate SSE transport configuration."""
        if self.transport_mode == TransportMode.SSE and (not self.host or not self.port):
            msg = "host and port must be configured for SSE transport mode"
            raise ValueError(msg)
        return self


def _get_env_value(key: str, prefix: str = "KEPLER_MCP_") -> str | None:
    """Get environment variable value with prefix."""
    return os.environ.get(f"{prefix}{key.upper()}")


def _load_env_config() -> dict[str, Any]:
    """Load configuration from environment variables."""
    env_mapping = {
        "app_name": "APP_NAME",
        "log_level": "LOG_LEVEL",
        "environment": "ENVIRONMENT",
        "host": "HOST",
        "port": "PORT",
        "enable_metrics": "ENABLE_METRICS",
        "transport_mode": "TRANSPORT_MODE",
        "sse_path": "SSE_PATH",
        "auth_token": "AUTH_TOKEN",
        "oauth_user_auth_enabled": "OAUTH_USER_AUTH_ENABLED",
        "oauth_authorization_url": "OAUTH_AUTHORIZATION_URL",
        "oauth_token_url": "OAUTH_TOKEN_URL",
        "oauth_client_id": "OAUTH_CLIENT_ID",
        "oauth_client_secret": "OAUTH_CLIENT_SECRET",
        "oauth_scope": "OAUTH_SCOPE",
        "oauth_redirect_uri": "OAUTH_REDIRECT_URI",
        "oauth_userinfo_url": "OAUTH_USERINFO_URL",
        "oauth_service_auth_enabled": "OAUTH_SERVICE_AUTH_ENABLED",
        "oauth_service_client_id": "OAUTH_SERVICE_CLIENT_ID",
        "oauth_service_client_secret": "OAUTH_SERVICE_CLIENT_SECRET",
        "oauth_service_token_url": "OAUTH_SERVICE_TOKEN_URL",
        "oauth_service_scope": "OAUTH_SERVICE_SCOPE",
        "token_encryption_key": "TOKEN_ENCRYPTION_KEY",
        "token_store_path": "TOKEN_STORE_PATH",
        "rate_limit_requests_per_minute": "RATE_LIMIT_REQUESTS_PER_MINUTE",
        "rate_limit_burst": "RATE_LIMIT_BURST",
        "gitlab_url": "GITLAB_URL",
    }

    config: dict[str, Any] = {}
    for field_name, env_suffix in env_mapping.items():
        value = _get_env_value(env_suffix)
        if value is not None:
            # Convert boolean strings
            if value.lower() in ("true", "false", "1", "0", "yes", "no"):
                value = value.lower() in ("true", "1", "yes")  # type: ignore[assignment]
            # Convert integer strings for known int fields
            elif field_name in ("port", "rate_limit_requests_per_minute", "rate_limit_burst"):
                with contextlib.suppress(ValueError):
                    value = int(value)  # type: ignore[assignment]
            config[field_name] = value

    return config


def _load_file_config(path: str | Path) -> dict[str, Any]:
    """Load configuration from a file (JSON or YAML)."""
    import json

    path = Path(path)
    if not path.exists():
        msg = f"Configuration file not found: {path}"
        raise ConfigError(msg)

    suffix = path.suffix.lower()
    content = path.read_text()

    if suffix == ".json":
        return dict(json.loads(content))

    if suffix in (".yaml", ".yml"):
        try:
            import yaml

            return dict(yaml.safe_load(content))
        except ImportError:
            msg = "PyYAML is required to load YAML configuration files"
            raise ConfigError(msg) from None

    msg = f"Unsupported configuration file format: {suffix}"
    raise ConfigError(msg)


def _redact_for_log(key: str, value: Any) -> str:
    """Redact sensitive values for logging."""
    secret_keys = {
        "auth_token",
        "oauth_client_secret",
        "oauth_service_client_secret",
        "token_encryption_key",
    }
    if key in secret_keys and value:
        return "***"
    return str(value)


def load_config(
    path: str | Path | None = None,
    cli_args: dict[str, Any] | None = None,
) -> Config:
    """Load and validate configuration.

    Precedence (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. Configuration file
    4. Model defaults

    Args:
        path: Optional path to configuration file
        cli_args: Optional CLI argument overrides

    Returns:
        Validated Config instance

    Raises:
        ConfigError: If configuration is invalid
    """
    # Load .env file if present
    load_dotenv()

    # Start with file config if provided
    config_dict: dict[str, Any] = {}
    if path:
        logger.debug("Loading configuration from file: %s", path)
        config_dict.update(_load_file_config(path))

    # Layer environment variables
    env_config = _load_env_config()
    for key, value in env_config.items():
        if value is not None:
            config_dict[key] = value
            logger.debug(
                "Config %s from environment: %s",
                key,
                _redact_for_log(key, value),
            )

    # Layer CLI arguments (highest priority)
    if cli_args:
        for key, value in cli_args.items():
            if value is not None:
                config_dict[key] = value
                logger.debug(
                    "Config %s from CLI: %s",
                    key,
                    _redact_for_log(key, value),
                )

    try:
        return Config(**config_dict)
    except Exception as e:
        msg = f"Configuration validation failed: {e}"
        raise ConfigError(msg) from e


def config_from_env() -> Config:
    """Load configuration from environment variables only.

    Convenience function that loads config with .env file support
    but no file-based configuration.

    Returns:
        Validated Config instance

    Raises:
        ConfigError: If configuration is invalid
    """
    return load_config()
