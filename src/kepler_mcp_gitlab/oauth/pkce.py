"""PKCE (Proof Key for Code Exchange) implementation.

Implements RFC 7636 for secure OAuth 2.0 Authorization Code flows.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PKCEPair:
    """PKCE code verifier and challenge pair.

    Used in OAuth 2.0 Authorization Code flow with PKCE
    to prevent authorization code interception attacks.

    Attributes:
        code_verifier: Random string sent with token request
        code_challenge: SHA256 hash of verifier sent with auth request
    """

    code_verifier: str
    code_challenge: str


def generate_code_verifier(nbytes: int = 32) -> str:
    """Generate a cryptographically random code verifier.

    Creates a code verifier string of 43-128 characters using
    URL-safe characters as specified in RFC 7636.

    Args:
        nbytes: Number of random bytes (minimum 32 for sufficient entropy)

    Returns:
        URL-safe code verifier string

    Raises:
        ValueError: If nbytes < 32
    """
    if nbytes < 32:
        msg = "nbytes must be at least 32 for sufficient entropy"
        raise ValueError(msg)

    return secrets.token_urlsafe(nbytes)


def generate_code_challenge(verifier: str) -> str:
    """Generate a code challenge from a code verifier.

    Computes the S256 code challenge as specified in RFC 7636:
    BASE64URL(SHA256(code_verifier))

    Args:
        verifier: The code verifier string

    Returns:
        Base64url-encoded SHA256 hash (without padding)
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    # Base64url encode without padding
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_pkce_pair(nbytes: int = 32) -> PKCEPair:
    """Create a new PKCE code verifier/challenge pair.

    Convenience function that generates both the verifier
    and corresponding challenge.

    Args:
        nbytes: Number of random bytes for verifier

    Returns:
        PKCEPair with verifier and challenge
    """
    verifier = generate_code_verifier(nbytes)
    challenge = generate_code_challenge(verifier)
    return PKCEPair(code_verifier=verifier, code_challenge=challenge)
