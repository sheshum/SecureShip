from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.sessions import ChatSessionState


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
