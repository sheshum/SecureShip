"""
The verification predicate itself. Kept separate from the registry/dispatcher
so "what does verified mean" and "who gets asked this question" stay
two small, independently-testable pieces.
"""

from dataclasses import dataclass

from app.services.auth_context import AuthContext
from app.schemas.sessions import ChatSessionState

@dataclass
class GateResult:
    """Result of an identity gate check."""

    allowed: bool


def enforce_gate(context: AuthContext) -> GateResult:
    """Deliberately dumb: one condition, no exceptions.
    
    A session is allowed access to verified tools only when BOTH:
    1. context.state == ChatSessionState.VERIFIED
    2. context.customer_id is not None
    
    If state and customer_id ever disagree, fail closed.
    This is the single point where "verified" is defined (Epic F3).
    """
    if context.state == ChatSessionState.VERIFIED and context.customer_id is not None:
        return GateResult(allowed=True)
    return GateResult(allowed=False)
