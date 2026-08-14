"""Authentication and verification endpoints."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException

from app.agent.prompts import VERIFICATION_EXHAUSTED_NOTE, VERIFICATION_SUCCEEDED_NOTE
from app.dependencies import (
    get_chat_session_repository,
    get_session_verification_repository,
)
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.session_verification import SessionVerificationRepository
from app.schemas.sessions import ChatSessionState
from app.schemas.verification import VerifyCodeRequest, VerifyCodeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _record_transcript_note(session_repo: ChatSessionRepository, session_id, content: str) -> None:
    session_repo.append_messages(
        session_id,
        [{"role": "system", "content": content, "tool_call_id": None, "tool_calls": None}],
    )


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(
    request: VerifyCodeRequest,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    verification_repo: Annotated[SessionVerificationRepository, Depends(get_session_verification_repository)],
    session_id: Annotated[UUID | None, Cookie()] = None,
) -> VerifyCodeResponse:
    """Verify an OTP code for a chat session.

    This is the ONLY code path that can set a session's state to "verified".

    Security enforcement (Epic F):
    - Checks code hash (SHA-256), never compares plain text
    - Enforces 3-attempt limit
    - Enforces 7-minute expiry
    - Returns neutral messages (no enumeration)

    Args:
        request: 6-digit code
        session_repo: Repository for chat sessions
        verification_repo: Repository for verification records
        session_id: Session ID from HttpOnly cookie

    Returns:
        VerifyCodeResponse with result and attempts_remaining if applicable

    Raises:
        HTTPException: 400 if no verification in progress or session not found
    """
    if session_id is None:
        raise HTTPException(status_code=400, detail="Session not found")

    session = session_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=400, detail="Session not found")

    verification = verification_repo.get_by_session(session_id)
    if verification is None:
        raise HTTPException(status_code=400, detail="No verification in progress")

    if verification.status == "verified":
        return VerifyCodeResponse(result="verified", attempts_remaining=None)

    if session.state not in [ChatSessionState.CODE_SENT, ChatSessionState.AWAITING_CODE]:
        raise HTTPException(status_code=400, detail="No verification in progress")

    now = datetime.now(UTC)
    if verification.expires_at < now:
        verification_repo.update_status(session_id, "expired")
        session_repo.update_session(session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None)
        _record_transcript_note(session_repo, session_id, VERIFICATION_EXHAUSTED_NOTE)
        return VerifyCodeResponse(result="expired", attempts_remaining=None)

    if verification.attempts >= 3:
        verification_repo.update_status(session_id, "exhausted")
        session_repo.update_session(session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None)
        _record_transcript_note(session_repo, session_id, VERIFICATION_EXHAUSTED_NOTE)
        return VerifyCodeResponse(result="expired", attempts_remaining=None)

    code_hash = hashlib.sha256(request.code.encode()).hexdigest()

    if code_hash != verification.code_hash:
        # Increment attempt counter
        updated = verification_repo.increment_attempt(session_id)
        if updated is None:
            raise HTTPException(status_code=500, detail="Failed to update attempts")

        # Update session state to awaiting_code
        session_repo.update_session(
            session_id,
            state=ChatSessionState.AWAITING_CODE,
            customer_id=session.customer_id,
        )

        # Check if this was the last attempt
        attempts_remaining = max(0, 3 - updated.attempts)
        if attempts_remaining == 0:
            verification_repo.update_status(session_id, "exhausted")
            session_repo.update_session(session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None)
            _record_transcript_note(session_repo, session_id, VERIFICATION_EXHAUSTED_NOTE)
            return VerifyCodeResponse(result="expired", attempts_remaining=0)

        return VerifyCodeResponse(result="incorrect", attempts_remaining=attempts_remaining)

    verification_repo.update_status(session_id, "verified")
    session_repo.update_session(
        session_id,
        state=ChatSessionState.VERIFIED,
        customer_id=verification.matched_customer_id,
    )
    _record_transcript_note(session_repo, session_id, VERIFICATION_SUCCEEDED_NOTE)

    return VerifyCodeResponse(result="verified", attempts_remaining=None)
