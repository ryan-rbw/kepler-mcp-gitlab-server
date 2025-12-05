"""Tests for token storage implementations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from pathlib import Path

from kepler_mcp_gitlab.oauth.flows import TokenSet
from kepler_mcp_gitlab.oauth.token_store import (
    EncryptedFileTokenStore,
    InMemoryTokenStore,
    TokenStoreError,
    create_token_store,
)


def create_test_tokens() -> TokenSet:
    """Create a TokenSet for testing."""
    return TokenSet(
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        token_type="Bearer",
        scope="read write",
    )


class TestInMemoryTokenStore:
    """Tests for InMemoryTokenStore class."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        """Test storing and retrieving tokens."""
        store = InMemoryTokenStore()
        tokens = create_test_tokens()

        await store.store_tokens("user1", tokens)
        retrieved = await store.get_tokens("user1")

        assert retrieved is not None
        assert retrieved.access_token == tokens.access_token
        assert retrieved.refresh_token == tokens.refresh_token

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        """Test retrieving non-existent tokens."""
        store = InMemoryTokenStore()
        result = await store.get_tokens("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_tokens(self) -> None:
        """Test deleting tokens."""
        store = InMemoryTokenStore()
        tokens = create_test_tokens()

        await store.store_tokens("user1", tokens)
        await store.delete_tokens("user1")

        result = await store.get_tokens("user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_user_isolation(self) -> None:
        """Test that users are isolated."""
        store = InMemoryTokenStore()

        tokens1 = create_test_tokens()
        tokens2 = TokenSet(
            access_token="other-token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        await store.store_tokens("user1", tokens1)
        await store.store_tokens("user2", tokens2)

        result1 = await store.get_tokens("user1")
        result2 = await store.get_tokens("user2")

        assert result1 is not None
        assert result2 is not None
        assert result1.access_token == "test-access-token"
        assert result2.access_token == "other-token"

    def test_clear(self) -> None:
        """Test clearing all tokens."""
        store = InMemoryTokenStore()
        store._tokens["user1"] = create_test_tokens()
        store._tokens["user2"] = create_test_tokens()

        store.clear()

        assert len(store._tokens) == 0


class TestEncryptedFileTokenStore:
    """Tests for EncryptedFileTokenStore class."""

    @pytest.fixture
    def encryption_key(self) -> str:
        """Generate a valid Fernet key."""
        return Fernet.generate_key().decode()

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary file path (not the file itself)."""
        return tmp_path / "tokens.enc"

    @pytest.mark.asyncio
    async def test_store_and_retrieve(
        self, encryption_key: str, temp_file: Path
    ) -> None:
        """Test storing and retrieving encrypted tokens."""
        store = EncryptedFileTokenStore(encryption_key, temp_file)
        tokens = create_test_tokens()

        await store.store_tokens("user1", tokens)
        retrieved = await store.get_tokens("user1")

        assert retrieved is not None
        assert retrieved.access_token == tokens.access_token
        assert retrieved.refresh_token == tokens.refresh_token

    @pytest.mark.asyncio
    async def test_file_is_encrypted(
        self, encryption_key: str, temp_file: Path
    ) -> None:
        """Test that file content is encrypted."""
        store = EncryptedFileTokenStore(encryption_key, temp_file)
        tokens = create_test_tokens()

        await store.store_tokens("user1", tokens)

        # Read raw file content
        content = temp_file.read_bytes()

        # Access token should not appear in plain text
        assert b"test-access-token" not in content

    @pytest.mark.asyncio
    async def test_persistence_across_instances(
        self, encryption_key: str, temp_file: Path
    ) -> None:
        """Test that tokens persist across store instances."""
        tokens = create_test_tokens()

        # Store with first instance
        store1 = EncryptedFileTokenStore(encryption_key, temp_file)
        await store1.store_tokens("user1", tokens)

        # Retrieve with new instance
        store2 = EncryptedFileTokenStore(encryption_key, temp_file)
        retrieved = await store2.get_tokens("user1")

        assert retrieved is not None
        assert retrieved.access_token == tokens.access_token

    @pytest.mark.asyncio
    async def test_wrong_key_fails(
        self, encryption_key: str, temp_file: Path
    ) -> None:
        """Test that wrong key fails to decrypt."""
        tokens = create_test_tokens()

        # Store with original key
        store1 = EncryptedFileTokenStore(encryption_key, temp_file)
        await store1.store_tokens("user1", tokens)

        # Try to read with different key
        wrong_key = Fernet.generate_key().decode()
        store2 = EncryptedFileTokenStore(wrong_key, temp_file)

        with pytest.raises(TokenStoreError, match="decrypt"):
            await store2.get_tokens("user1")

    def test_invalid_key_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid encryption key raises error."""
        with pytest.raises(TokenStoreError, match="Invalid encryption key"):
            EncryptedFileTokenStore("not-a-valid-key", tmp_path / "test.enc")


class TestCreateTokenStore:
    """Tests for create_token_store function."""

    def test_creates_in_memory_by_default(self) -> None:
        """Test that in-memory store is created by default."""
        store = create_token_store()
        assert isinstance(store, InMemoryTokenStore)

    def test_creates_file_store_with_path_and_key(self, tmp_path: Path) -> None:
        """Test that file store is created with path and key."""
        key = Fernet.generate_key().decode()
        store = create_token_store(
            encryption_key=key, file_path=str(tmp_path / "tokens.enc")
        )
        assert isinstance(store, EncryptedFileTokenStore)
