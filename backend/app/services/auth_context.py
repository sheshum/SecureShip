"""
Authentication context for tool execution.

Encapsulates the minimal verified session state needed to authorize and scope
tool calls, without coupling tools to the full ChatSession DB model.
"""

from dataclasses import dataclass
from uuid import UUID

from app.schemas.sessions import ChatSessionState


@dataclass(frozen=True)
class AuthContext:
    """Immutable authorization context derived from a verified session.
    
    Attributes:
        session_id: The chat session ID (for repository operations)
        customer_id: The verified customer ID (for data scoping), None if not verified
        state: The current session verification state
    """
    
    session_id: UUID
    customer_id: UUID | None
    state: ChatSessionState
