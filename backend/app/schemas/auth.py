from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.sessions import ChatSessionState


class StartVerificationRequest(BaseModel):
    session_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: str = Field(min_length=4, max_length=50)


class StartVerificationResponse(BaseModel):
    started: bool
    show_code_modal: bool
    state: ChatSessionState
    message: str
    error_code: str | None = None
    retry_at: datetime | None = None


class VerifyCodeRequest(BaseModel):
    session_id: UUID
    code: str = Field(min_length=1, max_length=20)


class VerifyCodeResponse(BaseModel):
    verified: bool
    state: ChatSessionState
    message: str
    error_code: str | None = None
    remaining_attempts: int | None = None
    pending_turn_id: str | None = None
