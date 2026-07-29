from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_auth_session_store,
    get_chat_session_repository,
    get_otp_service,
)
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.auth import VerifyCodeRequest, VerifyCodeResponse
from app.services.auth_session import AuthSessionStore
from app.services.otp import OtpService

router = APIRouter(tags=["auth"])


@router.post("/api/verify-code", response_model=VerifyCodeResponse)
def verify_code(
    request: VerifyCodeRequest,
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
) -> VerifyCodeResponse:
    session = session_repository.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    verify_result = otp_service.verify_code(request.session_id, request.code)
    if not verify_result.ok:
        if verify_result.error_code in {"expired_code", "too_many_attempts"}:
            auth_session_store.reset_identity_flow(request.session_id)
            session_repository.update_auth_state(
                request.session_id,
                state="collecting_identity",
                customer_id=None,
            )
            return VerifyCodeResponse(
                verified=False,
                state="collecting_identity",
                message="Verification expired. Please restart identity verification.",
                error_code=verify_result.error_code,
                remaining_attempts=verify_result.remaining_attempts,
            )

        session_repository.update_auth_state(
            request.session_id,
            state="awaiting_code",
            customer_id=None,
        )
        return VerifyCodeResponse(
            verified=False,
            state="awaiting_code",
            message="Invalid verification code.",
            error_code=verify_result.error_code,
            remaining_attempts=verify_result.remaining_attempts,
        )

    auth_record = auth_session_store.get(request.session_id)
    if auth_record is None or auth_record.pending_customer_id is None:
        auth_session_store.reset_identity_flow(request.session_id)
        session_repository.update_auth_state(
            request.session_id,
            state="collecting_identity",
            customer_id=None,
        )
        return VerifyCodeResponse(
            verified=False,
            state="collecting_identity",
            message="Identity verification context was lost. Please restart verification.",
            error_code="identity_missing",
        )

    auth_session_store.mark_verified(
        request.session_id,
        auth_record.pending_customer_id,
        now=datetime.now(UTC),
    )
    session_repository.update_auth_state(
        request.session_id,
        state="verified",
        customer_id=auth_record.pending_customer_id,
    )
    pending_turn = session_repository.get_pending_turn(request.session_id)
    pending_turn_id = (
        str(pending_turn.get("turn_id"))
        if isinstance(pending_turn, dict) and pending_turn.get("turn_id")
        else None
    )

    return VerifyCodeResponse(
        verified=True,
        state="verified",
        message="Verification successful.",
        remaining_attempts=verify_result.remaining_attempts,
        pending_turn_id=pending_turn_id,
    )
