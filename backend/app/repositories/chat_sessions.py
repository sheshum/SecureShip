from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ChatSession


class ChatSessionRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def list_sessions(self, *, include_deleted: bool = False) -> list[ChatSession]:
        with self._session_factory() as session:
            query = select(ChatSession)
            if not include_deleted:
                query = query.where(ChatSession.state != "deleted")
            query = query.order_by(ChatSession.started_at.desc())
            return session.scalars(query).all()

    def create_session(self, now: datetime) -> ChatSession:
        with self._session_factory() as session:
            chat_session = ChatSession(
                state="active",
                started_at=now,
                ended_at=None,
                transcript={"version": 1, "title": None, "events": []},
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def get_session(self, session_id: UUID, *, include_deleted: bool = False) -> ChatSession | None:
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None
            if not include_deleted and chat_session.state == "deleted":
                return None
            return chat_session

    def soft_delete_session(self, session_id: UUID, now: datetime) -> ChatSession | None:
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None
            chat_session.state = "deleted"
            chat_session.ended_at = now
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def append_events(self, session_id: UUID, events: list[dict[str, Any]]) -> ChatSession | None:
        if not events:
            return self.get_session(session_id)

        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None or chat_session.state == "deleted":
                return None

            transcript = self._normalize_transcript(chat_session.transcript)
            transcript["events"].extend(events)
            if not transcript.get("title"):
                transcript["title"] = self._derive_title_from_events(transcript["events"])
            chat_session.transcript = transcript

            session.commit()
            session.refresh(chat_session)
            return chat_session

    def set_title_if_missing(self, session_id: UUID, title: str) -> ChatSession | None:
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None or chat_session.state == "deleted":
                return None

            transcript = self._normalize_transcript(chat_session.transcript)
            if not transcript.get("title"):
                transcript["title"] = title
                chat_session.transcript = transcript
                session.commit()
                session.refresh(chat_session)
            return chat_session

    @staticmethod
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

    @staticmethod
    def _derive_title_from_events(events: list[dict[str, Any]]) -> str | None:
        for event in events:
            if event.get("type") == "message" and event.get("role") == "user":
                content = str(event.get("content") or "")
                normalized = " ".join(content.split()).strip()
                if not normalized:
                    continue
                if len(normalized) <= 60:
                    return normalized
                return f"{normalized[:57]}..."
        return None
