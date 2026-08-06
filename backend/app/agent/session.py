"""Agent session: immutable snapshot of session state for one turn."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.schemas.sessions import ChatSessionState


class SessionStateRefresher(Protocol):
    """Fetches current (state, customer_id) for a session from the store."""

    async def __call__(self, session_id: UUID) -> tuple[ChatSessionState, int | None]: ...


@dataclass(frozen=True)
class AgentSession:
    """Immutable snapshot of session state for agent execution.

    Bundles all session-related context needed for one turn.
    Caller is responsible for loading this from DB.

    Attributes:
        session_id: Unique session identifier
        customer_id: Verified customer ID (None if unverified)
        state: Current session state (anonymous, verified, etc.)
        history: Previous conversation messages (serialized)
    """

    session_id: UUID
    customer_id: int | None
    state: ChatSessionState
    history: list[dict]
