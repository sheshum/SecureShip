"""Authentication and verification endpoints."""

import hashlib
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_chat_session_repository,
    get_session_verification_repository,
)
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.session_verification import SessionVerificationRepository
from app.schemas.sessions import ChatSessionState
from app.schemas.verification import VerifyCodeRequest, VerifyCodeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(
    request: VerifyCodeRequest,
    session_repo: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    verification_repo: Annotated[
        SessionVerificationRepository, Depends(get_session_verification_repository)
    ],
) -> VerifyCodeResponse:
    """Verify an OTP code for a chat session.
    
    This is the ONLY code path that can set a session's state to "verified".
    
    Security enforcement (Epic F):
    - Checks code hash (SHA-256), never compares plain text
    - Enforces 3-attempt limit
    - Enforces 7-minute expiry
    - Returns neutral messages (no enumeration)
    
    Args:
        request: Session ID and 6-digit code
        session_repo: Repository for chat sessions
        verification_repo: Repository for verification records
    
    Returns:
        VerifyCodeResponse with result and attempts_remaining if applicable
    
    Raises:
        HTTPException: 400 if no verification in progress or session not found
    """
    # 1. Load the chat session
    session = session_repo.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=400, detail="Session not found")

    # 2. Load the verification record
    verification = verification_repo.get_by_session(request.session_id)
    if verification is None:
        raise HTTPException(status_code=400, detail="No verification in progress")

    # 3. Check if already verified (idempotent success)
    if verification.status == "verified":
        return VerifyCodeResponse(result="verified", attempts_remaining=None)

    # 4. Check current state - only pending/awaiting_code states can verify
    if session.state not in ["code_sent", "awaiting_code"]:
        raise HTTPException(status_code=400, detail="No verification in progress")

    # 5. Check expiry
    now = datetime.now(timezone.utc)
    if verification.expires_at < now:
        # Mark as expired
        verification_repo.update_status(request.session_id, "expired")
        session_repo.update_auth_state(
            request.session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None
        )
        return VerifyCodeResponse(result="expired", attempts_remaining=None)

    # 6. Check if attempts exhausted
    if verification.attempts >= 3:
        verification_repo.update_status(request.session_id, "exhausted")
        session_repo.update_auth_state(
            request.session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None
        )
        return VerifyCodeResponse(result="expired", attempts_remaining=None)

    # 7. Verify the code hash
    code_hash = hashlib.sha256(request.code.encode()).hexdigest()
    
    if code_hash != verification.code_hash:
        # Increment attempt counter
        updated = verification_repo.increment_attempt(request.session_id)
        if updated is None:
            raise HTTPException(status_code=500, detail="Failed to update attempts")
        
        # Update session state to awaiting_code
        session_repo.update_auth_state(
            request.session_id, state=ChatSessionState.AWAITING_CODE, customer_id=session.customer_id
        )
        
        # Check if this was the last attempt
        attempts_remaining = max(0, 3 - updated.attempts)
        if attempts_remaining == 0:
            verification_repo.update_status(request.session_id, "exhausted")
            session_repo.update_auth_state(
                request.session_id, state=ChatSessionState.CODE_EXPIRED, customer_id=None
            )
            return VerifyCodeResponse(result="expired", attempts_remaining=0)
        
        return VerifyCodeResponse(
            result="incorrect", 
            attempts_remaining=attempts_remaining
        )

    # 8. SUCCESS: Code is correct
    # This is the ONLY place that sets state = "verified"
    verification_repo.update_status(request.session_id, "verified")
    session_repo.update_auth_state(
        request.session_id,
        state=ChatSessionState.VERIFIED,
        customer_id=verification.matched_customer_id,
    )
    
    return VerifyCodeResponse(result="verified", attempts_remaining=None)
