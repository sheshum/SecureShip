from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionItem(BaseModel):
    id: UUID
    state: str
    started_at: datetime
    ended_at: datetime | None
    title: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]


class SessionCreateResponse(BaseModel):
    session: SessionItem


class SessionDeleteResponse(BaseModel):
    session: SessionItem
