from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_auth_session_store,
    get_chat_session_repository,
    get_identity_verification_service,
    get_otp_service,
    get_sms_service,
)
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.auth import (
    StartVerificationRequest,
    StartVerificationResponse,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from app.services.auth_session import AuthSessionStore
from app.services.identity_verification import IdentityVerificationService
from app.services.otp import OtpService
from app.services.sms import SmsService

router = APIRouter(tags=["auth"])


@router.post("/api/auth/start-verification", response_model=StartVerificationResponse)
def start_verification(
    request: StartVerificationRequest,
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    identity_service: Annotated[
        IdentityVerificationService, Depends(get_identity_verification_service)
    ],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    sms_service: Annotated[SmsService, Depends(get_sms_service)],
) -> StartVerificationResponse:
    session = session_repository.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.state == "verified" and session.customer_id is not None:
        return StartVerificationResponse(
            started=False,
            show_code_modal=False,
            state="verified",
            message="This session is already verified.",
            error_code="already_verified",
        )

    identity = identity_service.verify_identity(
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
    )
    if not identity.matched or identity.match is None:
        session_repository.update_auth_state(
            request.session_id,
            state="collecting_identity",
            customer_id=None,
        )
        return StartVerificationResponse(
            started=False,
            show_code_modal=False,
            state="collecting_identity",
            message="We could not verify your identity. Please check your details and try again.",
            error_code="identity_no_match",
        )

    pending_customer_id = UUID(identity.match.customer_id)
    otp_issue = otp_service.issue_code(
        request.session_id,
        pending_customer_id=pending_customer_id,
    )
    if not otp_issue.ok:
        return StartVerificationResponse(
            started=False,
            show_code_modal=False,
            state="awaiting_code",
            message="Please wait before requesting another verification code.",
            error_code=otp_issue.error_code,
            retry_at=otp_issue.retry_at,
        )

    sms_service.send_otp(request.phone_number, otp_issue.otp_code or "")
    session_repository.update_auth_state(
        request.session_id,
        state="code_sent",
        customer_id=None,
    )
    return StartVerificationResponse(
        started=True,
        show_code_modal=True,
        state="code_sent",
        message="Verification code sent. Enter the code to continue.",
    )


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

    return VerifyCodeResponse(
        verified=True,
        state="verified",
        message="Verification successful.",
        remaining_attempts=verify_result.remaining_attempts,
    )
