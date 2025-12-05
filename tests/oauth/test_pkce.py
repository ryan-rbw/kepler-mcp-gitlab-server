"""Tests for PKCE implementation."""

from __future__ import annotations

import base64
import hashlib

import pytest

from kepler_mcp_gitlab.oauth.pkce import (
    PKCEPair,
    create_pkce_pair,
    generate_code_challenge,
    generate_code_verifier,
)


class TestGenerateCodeVerifier:
    """Tests for generate_code_verifier function."""

    def test_generates_string(self) -> None:
        """Test that verifier is a string."""
        verifier = generate_code_verifier()
        assert isinstance(verifier, str)

    def test_sufficient_length(self) -> None:
        """Test that verifier has sufficient length."""
        verifier = generate_code_verifier()
        assert len(verifier) >= 43

    def test_unique_values(self) -> None:
        """Test that verifiers are unique."""
        verifiers = {generate_code_verifier() for _ in range(100)}
        assert len(verifiers) == 100

    def test_url_safe_characters(self) -> None:
        """Test that verifier uses URL-safe characters."""
        verifier = generate_code_verifier()
        # URL-safe base64 uses only these characters
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in allowed for c in verifier)

    def test_rejects_low_entropy(self) -> None:
        """Test that low entropy values are rejected."""
        with pytest.raises(ValueError, match="at least 32"):
            generate_code_verifier(nbytes=16)


class TestGenerateCodeChallenge:
    """Tests for generate_code_challenge function."""

    def test_generates_string(self) -> None:
        """Test that challenge is a string."""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert isinstance(challenge, str)

    def test_consistent_for_same_verifier(self) -> None:
        """Test that same verifier produces same challenge."""
        verifier = generate_code_verifier()
        challenge1 = generate_code_challenge(verifier)
        challenge2 = generate_code_challenge(verifier)
        assert challenge1 == challenge2

    def test_different_for_different_verifiers(self) -> None:
        """Test that different verifiers produce different challenges."""
        verifier1 = generate_code_verifier()
        verifier2 = generate_code_verifier()
        challenge1 = generate_code_challenge(verifier1)
        challenge2 = generate_code_challenge(verifier2)
        assert challenge1 != challenge2

    def test_s256_algorithm(self) -> None:
        """Test that S256 algorithm is correctly implemented."""
        verifier = "test_verifier_string"
        expected_hash = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_hash).rstrip(b"=").decode("ascii")

        challenge = generate_code_challenge(verifier)
        assert challenge == expected_challenge


class TestPKCEPair:
    """Tests for PKCEPair dataclass."""

    def test_is_frozen(self) -> None:
        """Test that PKCEPair is immutable."""
        pair = PKCEPair(code_verifier="verifier", code_challenge="challenge")

        with pytest.raises(AttributeError):
            pair.code_verifier = "new"  # type: ignore[misc]


class TestCreatePKCEPair:
    """Tests for create_pkce_pair function."""

    def test_creates_valid_pair(self) -> None:
        """Test that create_pkce_pair creates a valid pair."""
        pair = create_pkce_pair()

        assert pair.code_verifier is not None
        assert pair.code_challenge is not None

        # Verify challenge matches verifier
        expected_challenge = generate_code_challenge(pair.code_verifier)
        assert pair.code_challenge == expected_challenge
