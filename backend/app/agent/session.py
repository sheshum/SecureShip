"""Agent session: immutable snapshot of session state for one turn."""

from dataclasses import dataclass
from uuid import UUID

from app.schemas.sessions import ChatSessionState


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
