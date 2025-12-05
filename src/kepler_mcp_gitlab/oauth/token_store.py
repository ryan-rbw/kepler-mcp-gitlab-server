"""Token storage implementations.

Provides secure storage for OAuth tokens with encryption at rest.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken

from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.oauth.flows import TokenSet

if TYPE_CHECKING:
    from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow

logger = get_logger(__name__)


class TokenStoreError(Exception):
    """Error during token storage operations."""


class TokenStore(ABC):
    """Abstract base class for token storage.

    Token stores provide secure storage for OAuth tokens
    with optional encryption and persistence.
    """

    @abstractmethod
    async def store_tokens(self, user_id: str, tokens: TokenSet) -> None:
        """Store tokens for a user.

        Args:
            user_id: Unique user identifier
            tokens: TokenSet to store
        """

    @abstractmethod
    async def get_tokens(self, user_id: str) -> TokenSet | None:
        """Retrieve tokens for a user.

        Args:
            user_id: Unique user identifier

        Returns:
            TokenSet if found, None otherwise
        """

    @abstractmethod
    async def delete_tokens(self, user_id: str) -> None:
        """Remove tokens for a user.

        Args:
            user_id: Unique user identifier
        """

    async def refresh_if_needed(
        self,
        user_id: str,
        flow: OAuth2AuthorizationCodeFlow,
    ) -> TokenSet | None:
        """Check token expiry and refresh if needed.

        Args:
            user_id: Unique user identifier
            flow: OAuth flow for token refresh

        Returns:
            Current valid TokenSet, or None if no tokens exist
        """
        tokens = await self.get_tokens(user_id)
        if tokens is None:
            return None

        if tokens.needs_refresh and tokens.refresh_token:
            logger.debug("Refreshing tokens for user %s", user_id)
            try:
                new_tokens = await flow.refresh_access_token(tokens.refresh_token)
                await self.store_tokens(user_id, new_tokens)
                return new_tokens
            except Exception as e:
                logger.error("Failed to refresh tokens for user %s: %s", user_id, e)
                # Return existing tokens if refresh fails and they're not expired
                if not tokens.is_expired:
                    return tokens
                return None

        return tokens


class InMemoryTokenStore(TokenStore):
    """In-memory token storage.

    Tokens are stored in memory and lost on server restart.
    Suitable for development or when persistence is not required.
    """

    def __init__(self) -> None:
        """Initialize in-memory store."""
        self._tokens: dict[str, TokenSet] = {}
        self._lock = asyncio.Lock()

    async def store_tokens(self, user_id: str, tokens: TokenSet) -> None:
        """Store tokens in memory.

        Args:
            user_id: Unique user identifier
            tokens: TokenSet to store
        """
        async with self._lock:
            self._tokens[user_id] = tokens
            logger.debug("Stored tokens for user %s in memory", user_id)

    async def get_tokens(self, user_id: str) -> TokenSet | None:
        """Retrieve tokens from memory.

        Args:
            user_id: Unique user identifier

        Returns:
            TokenSet if found, None otherwise
        """
        async with self._lock:
            return self._tokens.get(user_id)

    async def delete_tokens(self, user_id: str) -> None:
        """Remove tokens from memory.

        Args:
            user_id: Unique user identifier
        """
        async with self._lock:
            if user_id in self._tokens:
                del self._tokens[user_id]
                logger.debug("Deleted tokens for user %s", user_id)

    def clear(self) -> None:
        """Clear all stored tokens."""
        self._tokens.clear()


class EncryptedFileTokenStore(TokenStore):
    """Encrypted file-based token storage.

    Tokens are encrypted using Fernet symmetric encryption
    and stored in a JSON file. Uses atomic writes to prevent
    corruption.
    """

    def __init__(self, encryption_key: str, file_path: str | Path) -> None:
        """Initialize encrypted file store.

        Args:
            encryption_key: Fernet-compatible encryption key
            file_path: Path to the token storage file

        Raises:
            TokenStoreError: If encryption key is invalid
        """
        try:
            self._fernet = Fernet(encryption_key.encode())
        except Exception as e:
            raise TokenStoreError(f"Invalid encryption key: {e}") from e

        self._file_path = Path(file_path)
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, str | float | None]] = {}
        self._loaded = False

    async def _load(self) -> None:
        """Load and decrypt token data from file."""
        if self._loaded:
            return

        if not self._file_path.exists():
            self._data = {}
            self._loaded = True
            return

        try:
            encrypted_data = self._file_path.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            self._data = json.loads(decrypted_data.decode())
            self._loaded = True
            logger.debug("Loaded tokens from %s", self._file_path)
        except InvalidToken:
            logger.error("Failed to decrypt token file - wrong key?")
            raise TokenStoreError("Failed to decrypt token file") from None
        except json.JSONDecodeError as e:
            logger.error("Failed to parse token file: %s", e)
            raise TokenStoreError(f"Failed to parse token file: {e}") from e

    async def _save(self) -> None:
        """Encrypt and save token data to file atomically."""
        json_data = json.dumps(self._data)
        encrypted_data = self._fernet.encrypt(json_data.encode())

        # Atomic write using temp file
        dir_path = self._file_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(dir=dir_path)
        temp_path = Path(temp_path_str)
        try:
            os.write(fd, encrypted_data)
            os.close(fd)
            temp_path.replace(self._file_path)
            logger.debug("Saved tokens to %s", self._file_path)
        except Exception:
            os.close(fd)
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _serialize_tokens(self, tokens: TokenSet) -> dict[str, str | float | None]:
        """Serialize TokenSet to dict for storage."""
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at.timestamp(),
            "token_type": tokens.token_type,
            "scope": tokens.scope,
        }

    def _deserialize_tokens(
        self, data: dict[str, str | float | None]
    ) -> TokenSet:
        """Deserialize dict to TokenSet."""
        expires_at_val = data.get("expires_at")
        if expires_at_val is None:
            msg = "Missing expires_at in token data"
            raise TokenStoreError(msg)

        return TokenSet(
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]) if data.get("refresh_token") else None,
            expires_at=datetime.fromtimestamp(float(expires_at_val), tz=UTC),
            token_type=str(data.get("token_type", "Bearer")),
            scope=str(data["scope"]) if data.get("scope") else None,
        )

    async def store_tokens(self, user_id: str, tokens: TokenSet) -> None:
        """Store tokens encrypted in file.

        Args:
            user_id: Unique user identifier
            tokens: TokenSet to store
        """
        async with self._lock:
            await self._load()
            self._data[user_id] = self._serialize_tokens(tokens)
            await self._save()
            logger.debug("Stored encrypted tokens for user %s", user_id)

    async def get_tokens(self, user_id: str) -> TokenSet | None:
        """Retrieve and decrypt tokens from file.

        Args:
            user_id: Unique user identifier

        Returns:
            TokenSet if found, None otherwise
        """
        async with self._lock:
            await self._load()
            data = self._data.get(user_id)
            if data is None:
                return None
            return self._deserialize_tokens(data)

    async def delete_tokens(self, user_id: str) -> None:
        """Remove tokens from file.

        Args:
            user_id: Unique user identifier
        """
        async with self._lock:
            await self._load()
            if user_id in self._data:
                del self._data[user_id]
                await self._save()
                logger.debug("Deleted encrypted tokens for user %s", user_id)


def create_token_store(
    encryption_key: str | None = None,
    file_path: str | Path | None = None,
) -> TokenStore:
    """Create appropriate token store based on configuration.

    Args:
        encryption_key: Optional Fernet encryption key
        file_path: Optional path for persistent storage

    Returns:
        Configured TokenStore instance
    """
    if file_path and encryption_key:
        return EncryptedFileTokenStore(encryption_key, file_path)
    return InMemoryTokenStore()
