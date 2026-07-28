from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import (
    SessionDetailResponse,
    SessionCreateResponse,
    SessionDeleteResponse,
    SessionItem,
    SessionListResponse,
    SessionTranscript,
    SessionTranscriptEvent,
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


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: UUID,
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionDetailResponse:
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        session=_to_session_item(session),
        transcript=_to_session_transcript(session.transcript),
    )


@router.delete("/{session_id}", response_model=SessionDeleteResponse)
def delete_session(
    session_id: UUID,
    repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionDeleteResponse:
    session = repository.delete_session(session_id, now=datetime.now(UTC))
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
def _to_session_transcript(transcript: dict[str, Any] | None) -> SessionTranscript:
    normalized = _normalize_transcript(transcript)
    events: list[SessionTranscriptEvent] = []

    for event in normalized["events"]:
        if not isinstance(event, dict):
            continue

        events.append(
            SessionTranscriptEvent(
                id=event.get("id") if isinstance(event.get("id"), str) else None,
                type=str(event.get("type") or "unknown"),
                role=event.get("role") if isinstance(event.get("role"), str) else None,
                content=event.get("content") if isinstance(event.get("content"), str) else None,
                created_at=(
                    event.get("created_at") if isinstance(event.get("created_at"), str) else None
                ),
                meta=event.get("meta") if isinstance(event.get("meta"), dict) else None,
                tool=event.get("tool") if isinstance(event.get("tool"), str) else None,
                args=event.get("args") if isinstance(event.get("args"), dict) else None,
                result=event.get("result") if isinstance(event.get("result"), dict) else None,
            )
        )

    return SessionTranscript(
        version=int(normalized.get("version") or 1),
        title=normalized.get("title") if isinstance(normalized.get("title"), str) else None,
        events=events,
    )
