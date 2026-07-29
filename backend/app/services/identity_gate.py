"""
The verification predicate itself. Kept separate from the registry/dispatcher
so "what does verified mean" and "who gets asked this question" stay
two small, independently-testable pieces.
"""

from dataclasses import dataclass

from app.models import ChatSession


@dataclass
class GateResult:
    """Result of an identity gate check."""

    allowed: bool


def enforce_gate(session: ChatSession) -> GateResult:
    """Deliberately dumb: one condition, no exceptions.
    
    A session is allowed access to verified tools only when BOTH:
    1. session.state == "verified"
    2. session.customer_id is not None
    
    If state and customer_id ever disagree, fail closed.
    This is the single point where "verified" is defined (Epic F3).
    """
    if session.state == "verified" and session.customer_id is not None:
        return GateResult(allowed=True)
    return GateResult(allowed=False)
