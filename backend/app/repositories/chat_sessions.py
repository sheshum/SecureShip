from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.db import SessionLocal
from app.models import ChatSession
from app.repositories.session_state_machine import SessionStateValidator
from app.schemas.sessions import ChatSessionState

# Sentinel value to distinguish "don't change" from "set to None"
_UNSET = object()


class ChatSessionRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None, settings: Settings | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._settings = settings or Settings()

    def list_sessions(
        self, limit: int = 100, offset: int = 0, state: ChatSessionState | None = None
    ) -> list[ChatSession]:
        with self._session_factory() as session:
            query = select(ChatSession).options(joinedload(ChatSession.customer))
            if state is not None:
                query = query.where(ChatSession.state == state)
            query = query.order_by(ChatSession.started_at.desc())
            query = query.limit(limit).offset(offset)
            return session.scalars(query).all()

    def count_sessions(self, state: ChatSessionState | None = None) -> int:
        """Return total count of sessions, optionally filtered by state."""
        with self._session_factory() as session:
            query = select(func.count()).select_from(ChatSession)
            if state is not None:
                query = query.where(ChatSession.state == state)
            return session.scalar(query) or 0

    def create_session(self, now: datetime) -> ChatSession:
        with self._session_factory() as session:
            expires_at = now + timedelta(seconds=self._settings.auth_session_ttl_seconds)
            chat_session = ChatSession(
                state=ChatSessionState.ANONYMOUS,
                started_at=now,
                ended_at=None,
                expires_at=expires_at,
                transcript={"messages": []},
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def get_session(self, session_id: UUID) -> ChatSession | None:
        """Return the active session, or None if not found, closed, or expired.

        Side-effect: sets ended_at when the session has passed its TTL.
        """
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None
            if chat_session.ended_at is not None:
                return None
            if chat_session.expires_at and datetime.now(UTC) >= chat_session.expires_at:
                self._mark_expired(chat_session, session)
                return None
            return chat_session

    def _mark_expired(self, chat_session: ChatSession, db_session: Session) -> None:
        chat_session.ended_at = datetime.now(UTC)
        db_session.commit()

    def touch_session(self, session_id: UUID, new_expires_at: datetime) -> None:
        """Extend session TTL (rolling window on activity)."""
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is not None and chat_session.ended_at is None:
                chat_session.expires_at = new_expires_at
                session.commit()

    def delete_session(self, session_id: UUID, now: datetime) -> ChatSession | None:
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None
            session.refresh(chat_session)
            chat_session.ended_at = now
            snapshot = ChatSession(
                id=chat_session.id,
                customer_id=chat_session.customer_id,
                state=chat_session.state,
                started_at=chat_session.started_at,
                ended_at=chat_session.ended_at,
                transcript=chat_session.transcript,
            )
            session.delete(chat_session)
            session.commit()
            return snapshot

    def set_conversation_messages(self, session_id: UUID, messages: list[dict[str, Any]]) -> ChatSession | None:
        """Store conversation messages as the transcript.

        Args:
            session_id: Session to update
            messages: List of serialized LLMMessage dicts (role, content, tool_calls, tool_call_id)

        Returns:
            Updated ChatSession or None if not found
        """
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None

            chat_session.transcript = {"messages": messages}

            session.commit()
            session.refresh(chat_session)
            return chat_session

    def append_messages(self, session_id: UUID, messages: list[dict[str, Any]]) -> ChatSession | None:
        """Append messages to the transcript.

        Used by non-agent code paths (e.g. /api/auth/verify-code) to record
        out-of-band events into the LLM-visible transcript.
        """
        if not messages:
            return self.get_session(session_id)

        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None

            transcript = self._normalize_transcript(chat_session.transcript)
            transcript["messages"].extend(messages)
            chat_session.transcript = transcript

            session.commit()
            session.refresh(chat_session)
            return chat_session

    def update_session(
        self,
        session_id: UUID,
        *,
        state: ChatSessionState | None = None,
        customer_id: UUID | object | None = _UNSET,
        ended_at: datetime | object | None = _UNSET,
    ) -> ChatSession | None:
        """Update session state and/or customer_id with validation.

        Uses a sentinel pattern to distinguish between:
        - Not changing customer_id (default, _UNSET sentinel)
        - Setting customer_id to None (explicit None value)
        - Setting customer_id to a UUID

        Args:
            session_id: Session to update
            state: New state (if None, state is not changed)
            customer_id: New customer_id value:
                - _UNSET (default): don't change customer_id
                - None: clear customer_id
                - UUID: set customer_id
            ended_at: Session end timestamp:
                - _UNSET (default): don't change ended_at
                - None: clear ended_at (reopen session)
                - datetime: set ended_at (close session)

        Returns:
            Updated ChatSession or None if not found

        Raises:
            ValueError: If state transition is invalid or violates invariants
        """
        with self._session_factory() as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None

            # Determine final values after update
            new_state = state if state is not None else chat_session.state
            new_customer_id = chat_session.customer_id if customer_id is _UNSET else customer_id

            # Validate state transition if state is changing
            if state is not None and state != chat_session.state:
                SessionStateValidator.validate_transition(
                    from_state=chat_session.state,
                    to_state=new_state,
                    new_customer_id=new_customer_id,
                )

            # Apply updates
            if state is not None:
                chat_session.state = state
            if customer_id is not _UNSET:
                chat_session.customer_id = customer_id
            if ended_at is not _UNSET:
                chat_session.ended_at = ended_at

            session.commit()
            session.refresh(chat_session)
            return chat_session

    def get_conversation_messages(
        self, session_id: UUID, *, preloaded: ChatSession | None = None
    ) -> list[dict[str, Any]]:
        """Get conversation history for LLM context.

        Pass `preloaded` to skip the DB lookup when the session is already in hand.
        Returns user, assistant, tool, and system messages with their full shape
        (including `tool_calls` on assistant messages and `tool_call_id` on tool
        results) so the LLM sees a coherent tool-call thread across turns.
        """
        chat_session = preloaded if preloaded is not None else self.get_session(session_id)
        if chat_session is None:
            return []

        transcript = self._normalize_transcript(chat_session.transcript)
        messages = transcript.get("messages")
        if not isinstance(messages, list):
            return []

        conversation: list[dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            role = str(msg.get("role") or "").strip()
            if role not in {"user", "assistant", "tool", "system"}:
                continue

            conversation.append(
                {
                    "role": role,
                    "content": msg.get("content") or "",
                    "tool_call_id": msg.get("tool_call_id"),
                    "tool_calls": msg.get("tool_calls"),
                }
            )

        return conversation

    @staticmethod
    def _normalize_transcript(transcript: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize transcript to {"messages": [...]} shape."""
        if not isinstance(transcript, dict):
            return {"messages": []}

        messages = transcript.get("messages")
        if not isinstance(messages, list):
            messages = []

        return {"messages": list(messages)}
