"""Session management for OAuth authentication.

Manages the association between MCP connections and authenticated users.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from kepler_mcp_gitlab.logging_config import get_logger
from kepler_mcp_gitlab.security import OAuthError, generate_secure_token

if TYPE_CHECKING:
    from kepler_mcp_gitlab.oauth.flows import OAuth2AuthorizationCodeFlow, TokenSet
    from kepler_mcp_gitlab.oauth.token_store import TokenStore

logger = get_logger(__name__)

# Default session timeout
DEFAULT_SESSION_TIMEOUT = timedelta(hours=24)


@dataclass
class Session:
    """Represents an authenticated user session.

    Attributes:
        session_id: Unique session identifier
        user_id: Associated user identifier
        created_at: Session creation timestamp
        last_accessed: Last activity timestamp
    """

    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(UTC)

    def is_expired(self, timeout: timedelta = DEFAULT_SESSION_TIMEOUT) -> bool:
        """Check if session has expired.

        Args:
            timeout: Session timeout duration

        Returns:
            True if session is expired
        """
        return datetime.now(UTC) > (self.last_accessed + timeout)


class SessionManager:
    """Manages authenticated user sessions.

    Thread-safe session management with token storage integration
    for automatic token refresh.
    """

    def __init__(
        self,
        token_store: TokenStore,
        oauth_flow: OAuth2AuthorizationCodeFlow | None = None,
        session_timeout: timedelta = DEFAULT_SESSION_TIMEOUT,
    ) -> None:
        """Initialize session manager.

        Args:
            token_store: Token storage backend
            oauth_flow: OAuth flow for token refresh
            session_timeout: Session expiration timeout
        """
        self._token_store = token_store
        self._oauth_flow = oauth_flow
        self._session_timeout = session_timeout
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, str] = {}  # user_id -> session_id
        self._lock = asyncio.Lock()

    async def create_session(self, user_id: str, tokens: TokenSet) -> str:
        """Create a new session for an authenticated user.

        Stores the tokens and creates a session association.

        Args:
            user_id: Unique user identifier
            tokens: OAuth tokens for the user

        Returns:
            New session ID
        """
        async with self._lock:
            # Store tokens
            await self._token_store.store_tokens(user_id, tokens)

            # Invalidate existing session for user
            if user_id in self._user_sessions:
                old_session_id = self._user_sessions[user_id]
                if old_session_id in self._sessions:
                    del self._sessions[old_session_id]

            # Create new session
            session_id = generate_secure_token(32)
            session = Session(session_id=session_id, user_id=user_id)

            self._sessions[session_id] = session
            self._user_sessions[user_id] = session_id

            logger.info("Created session %s for user %s", session_id[:8], user_id)

            return session_id

    async def get_session(self, session_id: str) -> Session | None:
        """Retrieve session by ID.

        Updates last accessed time if session is valid.

        Args:
            session_id: Session identifier

        Returns:
            Session if found and valid, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            if session.is_expired(self._session_timeout):
                logger.debug("Session %s has expired", session_id[:8])
                await self._cleanup_session(session)
                return None

            session.touch()
            return session

    async def get_auth_headers_for_session(
        self,
        session_id: str,
    ) -> dict[str, str]:
        """Get authorization headers for a session.

        Automatically refreshes tokens if needed.

        Args:
            session_id: Session identifier

        Returns:
            Authorization headers with valid token

        Raises:
            OAuthError: If session is invalid or token refresh fails
        """
        session = await self.get_session(session_id)
        if session is None:
            raise OAuthError("Invalid or expired session")

        # Get tokens, refreshing if needed
        if self._oauth_flow:
            tokens = await self._token_store.refresh_if_needed(
                session.user_id,
                self._oauth_flow,
            )
        else:
            tokens = await self._token_store.get_tokens(session.user_id)

        if tokens is None:
            raise OAuthError("No tokens found for session")

        if tokens.is_expired:
            raise OAuthError("Token has expired and cannot be refreshed")

        return {"Authorization": f"{tokens.token_type} {tokens.access_token}"}

    async def invalidate_session(self, session_id: str) -> None:
        """End a session and clean up.

        Args:
            session_id: Session identifier
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                await self._cleanup_session(session)
                logger.info("Invalidated session %s", session_id[:8])

    async def _cleanup_session(self, session: Session) -> None:
        """Clean up session data.

        Note: Does not delete tokens as user may have other sessions.

        Args:
            session: Session to clean up
        """
        if session.session_id in self._sessions:
            del self._sessions[session.session_id]
        if self._user_sessions.get(session.user_id) == session.session_id:
            del self._user_sessions[session.user_id]

    async def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed
        """
        async with self._lock:
            expired = [
                s for s in self._sessions.values()
                if s.is_expired(self._session_timeout)
            ]

            for session in expired:
                await self._cleanup_session(session)

            if expired:
                logger.debug("Cleaned up %d expired sessions", len(expired))

            return len(expired)

    async def get_session_count(self) -> int:
        """Get number of active sessions.

        Returns:
            Number of active sessions
        """
        async with self._lock:
            return len(self._sessions)

    async def get_user_session(self, user_id: str) -> Session | None:
        """Get session for a user.

        Args:
            user_id: User identifier

        Returns:
            Session if user has an active session, None otherwise
        """
        async with self._lock:
            session_id = self._user_sessions.get(user_id)
            if session_id is None:
                return None

            session = self._sessions.get(session_id)
            if session is None or session.is_expired(self._session_timeout):
                return None

            return session


class PendingAuthState:
    """Manages pending OAuth authorization states.

    Stores PKCE verifiers and state parameters during the
    OAuth authorization flow.
    """

    def __init__(self, timeout: timedelta = timedelta(minutes=10)) -> None:
        """Initialize pending state manager.

        Args:
            timeout: How long to keep pending states
        """
        self._states: dict[str, dict[str, str | datetime]] = {}
        self._timeout = timeout
        self._lock = asyncio.Lock()

    async def create_state(
        self,
        state: str,
        pkce_verifier: str,
    ) -> None:
        """Store pending authorization state.

        Args:
            state: OAuth state parameter
            pkce_verifier: PKCE code verifier
        """
        async with self._lock:
            self._states[state] = {
                "pkce_verifier": pkce_verifier,
                "created_at": datetime.now(UTC),
            }

    async def consume_state(self, state: str) -> str | None:
        """Retrieve and remove pending state.

        Args:
            state: OAuth state parameter

        Returns:
            PKCE verifier if state is valid, None otherwise
        """
        async with self._lock:
            data = self._states.pop(state, None)
            if data is None:
                return None

            created_at = data["created_at"]
            is_expired = (
                isinstance(created_at, datetime)
                and datetime.now(UTC) > (created_at + self._timeout)
            )
            if is_expired:
                logger.debug("State %s has expired", state[:8])
                return None

            verifier = data.get("pkce_verifier")
            return str(verifier) if verifier else None

    async def cleanup_expired(self) -> int:
        """Remove expired pending states.

        Returns:
            Number of states removed
        """
        async with self._lock:
            now = datetime.now(UTC)
            expired = [
                state for state, data in self._states.items()
                if isinstance(data["created_at"], datetime)
                and now > (data["created_at"] + self._timeout)
            ]

            for state in expired:
                del self._states[state]

            return len(expired)
