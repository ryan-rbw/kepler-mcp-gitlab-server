"""OAuth 2.0 module for Kepler MCP Server.

Provides OAuth 2.0 Authorization Code flow with PKCE for user authentication
and Client Credentials flow for service-to-service authentication.
"""

from kepler_mcp_gitlab.oauth.flows import (
    OAuth2AuthorizationCodeFlow,
    OAuth2ClientCredentialsFlow,
    TokenSet,
)
from kepler_mcp_gitlab.oauth.pkce import PKCEPair, generate_code_challenge, generate_code_verifier
from kepler_mcp_gitlab.oauth.session import Session, SessionManager
from kepler_mcp_gitlab.oauth.token_store import (
    EncryptedFileTokenStore,
    InMemoryTokenStore,
    TokenStore,
)

__all__ = [
    "EncryptedFileTokenStore",
    "InMemoryTokenStore",
    "OAuth2AuthorizationCodeFlow",
    "OAuth2ClientCredentialsFlow",
    "PKCEPair",
    "Session",
    "SessionManager",
    "TokenSet",
    "TokenStore",
    "generate_code_challenge",
    "generate_code_verifier",
]
