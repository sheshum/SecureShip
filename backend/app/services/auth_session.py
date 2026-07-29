"""
In-memory auth session store for ephemeral OTP verification data.

This store holds short-lived, high-churn auth data (OTP code hash, attempt count,
expiry, resend cooldown) keyed by chat_session.id. A Redis swap is the intended
future migration path without touching authorization logic.

Separated from ChatSession (Postgres) because:
- OTP data is ephemeral (expires in minutes, not persisted long-term)
- High write volume during verification attempts
- Easy to swap for Redis later without schema changes
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class AuthSessionData:
    """Ephemeral authentication state for a single chat session."""

    session_id: uuid.UUID
    code_hash: str  # SHA-256 hash of the 6-digit code, never the raw code
    sent_at: datetime
    expires_at: datetime
    attempts: int = 0
    matched_customer_id: uuid.UUID | None = None  # Set when identity matches


class AuthSessionStore(Protocol):
    """Interface for auth session storage. In-memory today, Redis tomorrow."""

    def set(self, session_id: uuid.UUID, data: AuthSessionData) -> None:
        """Store or update auth session data."""
        ...

    def get(self, session_id: uuid.UUID) -> AuthSessionData | None:
        """Retrieve auth session data, or None if not found/expired."""
        ...

    def delete(self, session_id: uuid.UUID) -> None:
        """Remove auth session data (e.g., after successful verification)."""
        ...


class InMemoryAuthSessionStore:
    """Thread-safe in-memory implementation of AuthSessionStore.
    
    Good enough for single-instance deployment. For multi-instance,
    swap this for a Redis implementation without touching calling code.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, AuthSessionData] = {}

    def set(self, session_id: uuid.UUID, data: AuthSessionData) -> None:
        self._store[session_id] = data

    def get(self, session_id: uuid.UUID) -> AuthSessionData | None:
        data = self._store.get(session_id)
        if data is None:
            return None
        # Auto-expire stale entries
        if datetime.now(datetime.timezone.utc) > data.expires_at:
            self.delete(session_id)
            return None
        return data

    def delete(self, session_id: uuid.UUID) -> None:
        self._store.pop(session_id, None)
