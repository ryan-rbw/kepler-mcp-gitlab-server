"""Tests for session management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from kepler_mcp_gitlab.oauth.flows import TokenSet
from kepler_mcp_gitlab.oauth.session import PendingAuthState, Session, SessionManager
from kepler_mcp_gitlab.oauth.token_store import InMemoryTokenStore
from kepler_mcp_gitlab.security import OAuthError


def create_test_tokens() -> TokenSet:
    """Create a TokenSet for testing."""
    return TokenSet(
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        token_type="Bearer",
        scope="read write",
    )


class TestSession:
    """Tests for Session dataclass."""

    def test_touch_updates_last_accessed(self) -> None:
        """Test that touch updates last_accessed."""
        session = Session(session_id="test", user_id="user1")
        original = session.last_accessed

        session.touch()

        assert session.last_accessed >= original

    def test_is_expired(self) -> None:
        """Test expiration check."""
        # Fresh session
        session = Session(session_id="test", user_id="user1")
        assert session.is_expired(timedelta(hours=1)) is False

        # Expired session
        session.last_accessed = datetime.now(UTC) - timedelta(hours=2)
        assert session.is_expired(timedelta(hours=1)) is True


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.fixture
    def token_store(self) -> InMemoryTokenStore:
        """Create an in-memory token store."""
        return InMemoryTokenStore()

    @pytest.fixture
    def session_manager(self, token_store: InMemoryTokenStore) -> SessionManager:
        """Create a session manager."""
        return SessionManager(token_store)

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager: SessionManager) -> None:
        """Test session creation."""
        tokens = create_test_tokens()
        session_id = await session_manager.create_session("user1", tokens)

        assert session_id is not None
        assert len(session_id) > 20  # Should be a secure token

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager: SessionManager) -> None:
        """Test session retrieval."""
        tokens = create_test_tokens()
        session_id = await session_manager.create_session("user1", tokens)

        session = await session_manager.get_session(session_id)

        assert session is not None
        assert session.user_id == "user1"

    @pytest.mark.asyncio
    async def test_get_invalid_session(self, session_manager: SessionManager) -> None:
        """Test retrieving invalid session."""
        session = await session_manager.get_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_invalidate_session(self, session_manager: SessionManager) -> None:
        """Test session invalidation."""
        tokens = create_test_tokens()
        session_id = await session_manager.create_session("user1", tokens)

        await session_manager.invalidate_session(session_id)

        session = await session_manager.get_session(session_id)
        assert session is None

    @pytest.mark.asyncio
    async def test_get_auth_headers(self, session_manager: SessionManager) -> None:
        """Test getting auth headers for session."""
        tokens = create_test_tokens()
        session_id = await session_manager.create_session("user1", tokens)

        headers = await session_manager.get_auth_headers_for_session(session_id)

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {tokens.access_token}"

    @pytest.mark.asyncio
    async def test_get_auth_headers_invalid_session(
        self, session_manager: SessionManager
    ) -> None:
        """Test getting auth headers for invalid session."""
        with pytest.raises(OAuthError, match="Invalid or expired session"):
            await session_manager.get_auth_headers_for_session("nonexistent")

    @pytest.mark.asyncio
    async def test_replaces_existing_session(
        self, session_manager: SessionManager
    ) -> None:
        """Test that creating a new session replaces the old one."""
        tokens1 = create_test_tokens()
        tokens2 = TokenSet(
            access_token="new-token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        session_id1 = await session_manager.create_session("user1", tokens1)
        session_id2 = await session_manager.create_session("user1", tokens2)

        # Old session should be invalid
        session1 = await session_manager.get_session(session_id1)
        assert session1 is None

        # New session should be valid
        session2 = await session_manager.get_session(session_id2)
        assert session2 is not None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, session_manager: SessionManager) -> None:
        """Test cleanup of expired sessions."""
        tokens = create_test_tokens()
        session_id = await session_manager.create_session("user1", tokens)

        # Manually expire the session
        session = session_manager._sessions[session_id]
        session.last_accessed = datetime.now(UTC) - timedelta(days=2)

        # Cleanup should remove it
        count = await session_manager.cleanup_expired()
        assert count == 1

        # Session should be gone
        session = await session_manager.get_session(session_id)
        assert session is None


class TestPendingAuthState:
    """Tests for PendingAuthState class."""

    @pytest.mark.asyncio
    async def test_create_and_consume_state(self) -> None:
        """Test creating and consuming auth state."""
        manager = PendingAuthState()

        await manager.create_state("state123", "verifier456")
        verifier = await manager.consume_state("state123")

        assert verifier == "verifier456"

    @pytest.mark.asyncio
    async def test_consume_removes_state(self) -> None:
        """Test that consuming removes state."""
        manager = PendingAuthState()

        await manager.create_state("state123", "verifier456")
        await manager.consume_state("state123")

        # Second consume should return None
        verifier = await manager.consume_state("state123")
        assert verifier is None

    @pytest.mark.asyncio
    async def test_consume_nonexistent(self) -> None:
        """Test consuming non-existent state."""
        manager = PendingAuthState()
        verifier = await manager.consume_state("nonexistent")
        assert verifier is None

    @pytest.mark.asyncio
    async def test_expired_state_returns_none(self) -> None:
        """Test that expired state returns None."""
        manager = PendingAuthState(timeout=timedelta(seconds=0))

        await manager.create_state("state123", "verifier456")
        # State expires immediately

        verifier = await manager.consume_state("state123")
        assert verifier is None
