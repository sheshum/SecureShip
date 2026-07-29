from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_chat_session_repository
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import (
    SessionCreateResponse,
    SessionItem,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.post("", response_model=SessionCreateResponse)
def create_session(
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionCreateResponse:
    session = repository.create_session(now=datetime.now(UTC))
    return SessionCreateResponse(
        session=SessionItem(
            id=session.id,
            state=session.state,
            started_at=session.started_at,
            ended_at=session.ended_at,
            title="Support chat",
        )
    )
