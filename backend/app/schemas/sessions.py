from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatSessionState(str, Enum):
    """Session authentication state."""

    ANONYMOUS = "anonymous"
    COLLECTING_IDENTITY = "collecting_identity"
    CODE_SENT = "code_sent"
    AWAITING_CODE = "awaiting_code"
    VERIFIED = "verified"
    ESCALATED_TO_HUMAN = "escalated_to_human"
    CODE_EXPIRED = "code_expired"


class SessionItem(BaseModel):
    id: UUID
    state: ChatSessionState
    started_at: datetime
    ended_at: datetime | None


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]


class SessionCreateResponse(BaseModel):
    session: SessionItem


class SessionDeleteResponse(BaseModel):
    session: SessionItem


class SessionUpdateRequest(BaseModel):
    """Request to update session fields (e.g., set ended_at to close session)."""

    ended_at: datetime | None = None


class SessionTranscriptEvent(BaseModel):
    id: str | None = None
    type: str
    role: str | None = None
    content: str | None = None
    created_at: str | None = None
    meta: dict[str, Any] | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class SessionTranscript(BaseModel):
    version: int
    title: str | None = None
    events: list[SessionTranscriptEvent]


class SessionDetailResponse(BaseModel):
    session: SessionItem
    transcript: SessionTranscript
