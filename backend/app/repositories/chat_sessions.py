from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db import SessionLocal
from app.models import ChatSession
from app.repositories.session_state_machine import SessionStateValidator
from app.schemas.sessions import ChatSessionState

# Sentinel value to distinguish "don't change" from "set to None"
_UNSET = object()


class ChatSessionRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

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
            chat_session = ChatSession(
                state=ChatSessionState.ANONYMOUS,
                started_at=now,
                ended_at=None,
                transcript={"version": 2, "messages": []},
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def get_session(self, session_id: UUID) -> ChatSession | None:
        with self._session_factory() as session:
            return session.get(ChatSession, session_id)

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

    def set_conversation_messages(
        self, session_id: UUID, messages: list[dict[str, Any]]
    ) -> ChatSession | None:
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

            chat_session.transcript = {
                "version": 2,
                "messages": messages,
            }

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

    def get_conversation_messages(self, session_id: UUID) -> list[dict[str, str]]:
        """Get conversation history for LLM context.

        Returns only user/assistant messages, excluding system prompts and tool-role messages.
        """
        chat_session = self.get_session(session_id)
        if chat_session is None:
            return []

        transcript = self._normalize_transcript(chat_session.transcript)
        messages = transcript.get("messages")
        if not isinstance(messages, list):
            return []

        conversation: list[dict[str, str]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            role = str(msg.get("role") or "").strip()
            content = str(msg.get("content") or "").strip()

            # Only include user/assistant messages for conversation context
            if role not in {"user", "assistant"} or not content:
                continue

            conversation.append({"role": role, "content": content})

        return conversation

    @staticmethod
    def _normalize_transcript(transcript: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize transcript to v2 format."""
        if not isinstance(transcript, dict):
            return {"version": 2, "messages": []}

        messages = transcript.get("messages")
        if not isinstance(messages, list):
            messages = []

        return {
            "version": 2,
            "messages": list(messages),
        }
