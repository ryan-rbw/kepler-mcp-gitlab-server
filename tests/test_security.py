"""Tests for security module."""

from __future__ import annotations

import pytest

from kepler_mcp_gitlab.config import Config
from kepler_mcp_gitlab.security import (
    NoAuthStrategy,
    StaticTokenAuthStrategy,
    build_auth_strategy,
    constant_time_equals,
    generate_secure_token,
    mask_sensitive_data,
    redact,
    validate_shared_token,
)


class TestRedact:
    """Tests for redact function."""

    def test_redact_non_empty(self) -> None:
        """Test that non-empty values are redacted."""
        assert redact("secret123") == "***"
        assert redact("a") == "***"

    def test_redact_empty(self) -> None:
        """Test that empty values show <empty>."""
        assert redact("") == "<empty>"
        assert redact(None) == "<empty>"


class TestConstantTimeEquals:
    """Tests for constant_time_equals function."""

    def test_equal_strings(self) -> None:
        """Test equal strings return True."""
        assert constant_time_equals("abc", "abc") is True

    def test_unequal_strings(self) -> None:
        """Test unequal strings return False."""
        assert constant_time_equals("abc", "def") is False

    def test_none_values(self) -> None:
        """Test None handling."""
        assert constant_time_equals(None, None) is True
        assert constant_time_equals(None, "abc") is False
        assert constant_time_equals("abc", None) is False


class TestValidateSharedToken:
    """Tests for validate_shared_token function."""

    def test_both_empty(self) -> None:
        """Test both empty passes."""
        assert validate_shared_token(None, None) is True
        assert validate_shared_token("", "") is True
        assert validate_shared_token(None, "") is True

    def test_expected_empty_provided_not(self) -> None:
        """Test empty expected with non-empty provided fails."""
        assert validate_shared_token(None, "token") is False
        assert validate_shared_token("", "token") is False

    def test_matching_tokens(self) -> None:
        """Test matching tokens pass."""
        assert validate_shared_token("secret", "secret") is True

    def test_mismatched_tokens(self) -> None:
        """Test mismatched tokens fail."""
        assert validate_shared_token("secret", "wrong") is False


class TestGenerateSecureToken:
    """Tests for generate_secure_token function."""

    def test_generates_string(self) -> None:
        """Test that token is a string."""
        token = generate_secure_token()
        assert isinstance(token, str)

    def test_generates_unique(self) -> None:
        """Test that tokens are unique."""
        tokens = {generate_secure_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_custom_length(self) -> None:
        """Test custom byte length."""
        token_16 = generate_secure_token(16)
        token_64 = generate_secure_token(64)
        assert len(token_16) < len(token_64)


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data function."""

    def test_masks_sensitive_keys(self) -> None:
        """Test that sensitive keys are masked."""
        data = {
            "username": "john",
            "password": "secret123",
            "access_token": "abc123",
        }
        masked = mask_sensitive_data(data)

        assert masked["username"] == "john"
        assert masked["password"] == "***"
        assert masked["access_token"] == "***"

    def test_handles_nested_dicts(self) -> None:
        """Test that nested dicts are handled."""
        data = {
            "user": {
                "name": "john",
                "api_token": "secret",
            }
        }
        masked = mask_sensitive_data(data)

        assert masked["user"]["name"] == "john"
        assert masked["user"]["api_token"] == "***"


class TestAuthStrategies:
    """Tests for authentication strategies."""

    @pytest.mark.asyncio
    async def test_no_auth_strategy(self) -> None:
        """Test NoAuthStrategy returns empty headers."""
        strategy = NoAuthStrategy()
        headers = await strategy.get_auth_headers()
        assert headers == {}

    @pytest.mark.asyncio
    async def test_static_token_strategy(self) -> None:
        """Test StaticTokenAuthStrategy returns token header."""
        strategy = StaticTokenAuthStrategy("Authorization", "Bearer abc123")
        headers = await strategy.get_auth_headers()
        assert headers == {"Authorization": "Bearer abc123"}


class TestBuildAuthStrategy:
    """Tests for build_auth_strategy function."""

    def test_no_auth_by_default(self) -> None:
        """Test that NoAuthStrategy is returned by default."""
        config = Config()
        strategy = build_auth_strategy(config)
        assert isinstance(strategy, NoAuthStrategy)

    def test_static_token_with_auth_token(self) -> None:
        """Test that StaticTokenAuthStrategy is used with auth_token."""
        config = Config(auth_token="my-token")
        strategy = build_auth_strategy(config)
        assert isinstance(strategy, StaticTokenAuthStrategy)
