from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

ChatSessionState = Literal[
    "anonymous",
    "collecting_identity",
    "code_sent",
    "awaiting_code",
    "verified",
    "escalated_to_human",
]

class SessionItem(BaseModel):
    id: UUID
    state: ChatSessionState
    started_at: datetime
    ended_at: datetime | None
    title: str


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]


class SessionCreateResponse(BaseModel):
    session: SessionItem


class SessionDeleteResponse(BaseModel):
    session: SessionItem


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
