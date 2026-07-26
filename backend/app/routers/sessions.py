from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import (
    SessionCreateResponse,
    SessionDeleteResponse,
    SessionItem,
    SessionListResponse,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
def list_sessions(
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionListResponse:
    sessions = repository.list_sessions()
    return SessionListResponse(sessions=[_to_session_item(session) for session in sessions])


@router.post("", response_model=SessionCreateResponse)
def create_session(
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionCreateResponse:
    session = repository.create_session(now=datetime.now(UTC))
    return SessionCreateResponse(session=_to_session_item(session))


@router.delete("/{session_id}", response_model=SessionDeleteResponse)
def delete_session(
    session_id: UUID,
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionDeleteResponse:
    session = repository.soft_delete_session(session_id, now=datetime.now(UTC))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDeleteResponse(session=_to_session_item(session))


def _to_session_item(session: ChatSession) -> SessionItem:
    transcript = _normalize_transcript(session.transcript)
    title = _derive_title(transcript)
    return SessionItem(
        id=session.id,
        state=session.state,
        started_at=session.started_at,
        ended_at=session.ended_at,
        title=title,
        message_count=_count_message_events(transcript),
    )


def _normalize_transcript(transcript: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(transcript, dict):
        return {"version": 1, "title": None, "events": []}
    events = transcript.get("events")
    if not isinstance(events, list):
        events = []
    return {
        "version": transcript.get("version", 1),
        "title": transcript.get("title"),
        "events": events,
    }


def _derive_title(transcript: dict[str, Any]) -> str:
    title = transcript.get("title")
    if isinstance(title, str) and title.strip():
        return title

    for event in transcript.get("events", []):
        if event.get("type") == "message" and event.get("role") == "user":
            content = " ".join(str(event.get("content") or "").split()).strip()
            if not content:
                continue
            if len(content) <= 60:
                return content
            return f"{content[:57]}..."

    return "New chat"


def _count_message_events(transcript: dict[str, Any]) -> int:
    count = 0
    for event in transcript.get("events", []):
        if event.get("type") == "message":
            count += 1
    return count
