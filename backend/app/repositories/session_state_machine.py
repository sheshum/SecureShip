"""Session state transition validation logic."""

from typing import ClassVar
from uuid import UUID

from app.schemas.sessions import ChatSessionState


class SessionStateValidator:
    """Validates session state transitions and invariants.

    Enforces the documented state machine flow and business rules:
    - VERIFIED state requires customer_id to be set
    - CODE_EXPIRED should clear customer_id
    - Invalid transitions are rejected
    - Same-state transitions are allowed (no-op)
    """

    # Valid state transitions (from_state, to_state)
    VALID_TRANSITIONS: ClassVar[set[tuple[ChatSessionState, ChatSessionState]]] = {
        # Initial flow: anonymous -> identity verification
        (ChatSessionState.ANONYMOUS, ChatSessionState.CODE_SENT),
        (ChatSessionState.ANONYMOUS, ChatSessionState.COLLECTING_IDENTITY),
        # OTP flow
        (ChatSessionState.CODE_SENT, ChatSessionState.AWAITING_CODE),
        (ChatSessionState.CODE_SENT, ChatSessionState.VERIFIED),
        (
            ChatSessionState.AWAITING_CODE,
            ChatSessionState.AWAITING_CODE,
        ),  # retry with same customer
        (ChatSessionState.AWAITING_CODE, ChatSessionState.VERIFIED),
        (ChatSessionState.AWAITING_CODE, ChatSessionState.CODE_EXPIRED),
        (ChatSessionState.CODE_SENT, ChatSessionState.CODE_EXPIRED),
        # Recovery flows
        (ChatSessionState.CODE_EXPIRED, ChatSessionState.ANONYMOUS),
        (ChatSessionState.CODE_EXPIRED, ChatSessionState.COLLECTING_IDENTITY),
        (ChatSessionState.CODE_EXPIRED, ChatSessionState.CODE_SENT),
        # Human escalation (from any state)
        (ChatSessionState.ANONYMOUS, ChatSessionState.ESCALATED_TO_HUMAN),
        (ChatSessionState.COLLECTING_IDENTITY, ChatSessionState.ESCALATED_TO_HUMAN),
        (ChatSessionState.CODE_SENT, ChatSessionState.ESCALATED_TO_HUMAN),
        (ChatSessionState.AWAITING_CODE, ChatSessionState.ESCALATED_TO_HUMAN),
        (ChatSessionState.CODE_EXPIRED, ChatSessionState.ESCALATED_TO_HUMAN),
        (ChatSessionState.VERIFIED, ChatSessionState.ESCALATED_TO_HUMAN),
        # Collecting identity transitions
        (ChatSessionState.COLLECTING_IDENTITY, ChatSessionState.CODE_SENT),
        (ChatSessionState.COLLECTING_IDENTITY, ChatSessionState.ANONYMOUS),  # rejection/restart
        # Post-escalation: Melany can still guide an anonymous user through verification
        (ChatSessionState.ESCALATED_TO_HUMAN, ChatSessionState.COLLECTING_IDENTITY),
        (ChatSessionState.ESCALATED_TO_HUMAN, ChatSessionState.CODE_SENT),
    }

    @staticmethod
    def validate_transition(
        from_state: ChatSessionState,
        to_state: ChatSessionState,
        new_customer_id: UUID | None,
    ) -> None:
        """Validate a state transition and customer_id relationship.

        Args:
            from_state: Current session state
            to_state: Desired new state
            new_customer_id: New customer_id value (after update)

        Raises:
            ValueError: If transition is invalid or invariants are violated
        """
        # Same-state transitions are always allowed (no-op)
        if from_state == to_state:
            return

        # Check if transition is in the valid set
        if (from_state, to_state) not in SessionStateValidator.VALID_TRANSITIONS:
            raise ValueError(f"Invalid state transition: {from_state} -> {to_state}")

        # Enforce state-specific invariants for the target state
        SessionStateValidator._enforce_target_state_invariants(to_state, new_customer_id)

    @staticmethod
    def _enforce_target_state_invariants(state: ChatSessionState, customer_id: UUID | None) -> None:
        """Enforce invariants for a target state.

        Args:
            state: The state being transitioned to
            customer_id: The customer_id value after the transition

        Raises:
            ValueError: If state invariants are violated
        """
        # VERIFIED state MUST have customer_id set
        if state == ChatSessionState.VERIFIED and customer_id is None:
            raise ValueError("VERIFIED state requires customer_id to be set")

        # CODE_EXPIRED should have customer_id cleared (warning only in practice,
        # but we enforce it here for consistency)
        if state == ChatSessionState.CODE_EXPIRED and customer_id is not None:
            raise ValueError("CODE_EXPIRED state should have customer_id cleared")

        # ANONYMOUS should have no customer association
        if state == ChatSessionState.ANONYMOUS and customer_id is not None:
            raise ValueError("ANONYMOUS state should have customer_id cleared")
