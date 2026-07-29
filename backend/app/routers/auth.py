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
    pass
