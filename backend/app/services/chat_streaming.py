from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import ChatSessionState
from app.services.auth_session import AuthSessionStore


@dataclass(frozen=True, slots=True)
class ChatSessionContext:
    session_id: UUID
    chat_session: ChatSession


@dataclass(frozen=True, slots=True)
class AuthGateDecision:
    state: ChatSessionState
    auth_expires_at: str | None
    verified_customer_id: UUID | None

    @property
    def requires_auth(self) -> bool:
        return self.verified_customer_id is None

    @property
    def should_show_code_modal(self) -> bool:
        return self.state in {"code_sent", "awaiting_code"}


def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def session_event(session_id: UUID) -> dict:
    return {"type": "session", "session_id": str(session_id)}


def auth_state_event(state: ChatSessionState, *, auth_expires_at: str | None = None) -> dict:
    payload: dict[str, str] = {"type": "auth_state", "state": state}
    if auth_expires_at is not None:
        payload["auth_expires_at"] = auth_expires_at
    return payload


def auth_required_event(
    *,
    pending_turn_id: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "type": "auth_required",
        "message": message
        or "Please share your first name, last name, and phone number to verify your identity before I can access shipment details.",
        "cta": {
            "label": "Reply with identity details",
            "action": "reply_with_identity",
        },
        "pending_turn_id": pending_turn_id,
    }


def show_code_modal_event() -> dict:
    return {
        "type": "show_code_modal",
        "open": True,
    }


def done_event() -> dict:
    return {"type": "done"}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def new_event_id() -> str:
    return f"evt_{uuid4().hex}"


def resolve_or_create_session(
    request_session_id: UUID | None,
    session_repository: ChatSessionRepository,
    *,
    now: datetime,
) -> ChatSessionContext:
    if request_session_id is None:
        chat_session = session_repository.create_session(now=now)
        return ChatSessionContext(session_id=chat_session.id, chat_session=chat_session)

    chat_session = session_repository.get_session(request_session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSessionContext(session_id=request_session_id, chat_session=chat_session)


def resolve_auth_gate(
    session_context: ChatSessionContext,
    session_repository: ChatSessionRepository,
    auth_session_store: AuthSessionStore,
    *,
    now: datetime,
) -> AuthGateDecision:
    session_id = session_context.session_id
    chat_session = session_context.chat_session

    auth_state: ChatSessionState = chat_session.state
    auth_expires_at: str | None = None
    verified_customer_id = chat_session.customer_id
    auth_lookup = auth_session_store.expire_if_needed(session_id, now=now)

    if auth_lookup.status in {"expired", "missing"}:
        auth_session_store.mark_auth_required(session_id, now=now)
        session_repository.update_auth_state(
            session_id,
            state="collecting_identity",
            customer_id=None,
        )
        return AuthGateDecision(
            state="collecting_identity",
            auth_expires_at=None,
            verified_customer_id=None,
        )

    auth_record = auth_lookup.session
    if (
        auth_record is not None
        and auth_record.auth_state == "verified"
        and auth_record.verified_customer_id is not None
    ):
        auth_expires_at = (
            auth_record.auth_expires_at.isoformat().replace("+00:00", "Z")
            if auth_record.auth_expires_at is not None
            else None
        )
        session_repository.update_auth_state(
            session_id,
            state="verified",
            customer_id=auth_record.verified_customer_id,
        )
        return AuthGateDecision(
            state="verified",
            auth_expires_at=auth_expires_at,
            verified_customer_id=auth_record.verified_customer_id,
        )

    if chat_session.state not in {"collecting_identity", "code_sent", "awaiting_code"}:
        auth_state = "collecting_identity"

    session_repository.update_auth_state(
        session_id,
        state=auth_state,
        customer_id=None,
    )
    return AuthGateDecision(
        state=auth_state,
        auth_expires_at=None,
        verified_customer_id=None,
    )


def user_message_event(content: str) -> dict:
    return {
        "id": new_event_id(),
        "type": "message",
        "role": "user",
        "content": content,
        "created_at": utc_now_iso(),
        "meta": {"source": "ui"},
    }


def tool_transcript_event(stream_event: dict, *, turn_id: str) -> dict:
    event_type = str(stream_event.get("type") or "tool_result")
    payload = {
        "id": new_event_id(),
        "type": event_type,
        "created_at": utc_now_iso(),
        "meta": {"turn_id": turn_id},
        "tool": stream_event.get("tool"),
    }
    if event_type == "tool_call":
        payload["args"] = stream_event.get("args")
    else:
        payload["result"] = stream_event.get("result")
    return payload


def assistant_message_event(content: str, *, turn_id: str) -> dict:
    return {
        "id": new_event_id(),
        "type": "message",
        "role": "assistant",
        "content": content,
        "created_at": utc_now_iso(),
        "meta": {"turn_id": turn_id, "finish_reason": "done"},
    }
