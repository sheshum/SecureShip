"""Chat endpoints: public conversation with the LLM agent."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from app.agent import Agent, AgentSession
from app.core.config import Settings
from app.core.exceptions import SessionExpiredError
from app.dependencies import get_agent, get_chat_session_repository, get_settings
from app.llm.base import LLMError
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest, ChatResponse, RestoredMessage, SessionRestoreResponse
from app.schemas.sessions import ChatSessionState

router = APIRouter(prefix="/api/chat", tags=["chat"])

_COOKIE_NAME = "session_id"


def _cookie_attrs_for_request(request: Request) -> dict:
    # `SameSite=strict` can block cookies in local proxy setups (frontend dev server
    # proxying to backend). Relax to `lax` for localhost development only.
    local_hosts = {"localhost", "127.0.0.1"}
    samesite = "lax" if request.url.hostname in local_hosts else "strict"
    return {"httponly": True, "samesite": samesite, "path": "/"}


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    response: Response,
    http_request: Request,
    agent: Annotated[Agent, Depends(get_agent)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_id: Annotated[UUID | None, Cookie()] = None,
) -> ChatResponse:
    """Chat endpoint: delegate to Agent for agentic loop execution."""
    # Resolve or create session from cookie
    if session_id is not None:
        chat_session = session_repo.get_session(session_id)
        if chat_session is None:
            raise SessionExpiredError()
    else:
        chat_session = session_repo.create_session(datetime.now(UTC))

    # Build agent session (snapshot of current state)
    agent_session = AgentSession(
        session_id=chat_session.id,
        customer_id=chat_session.customer_id,
        state=chat_session.state,
        history=session_repo.get_conversation_messages(chat_session.id, preloaded=chat_session),
    )

    # Execute agent turn (pure orchestration, no DB)
    async def _refresh_state(session_id: UUID) -> tuple[ChatSessionState, int | None]:
        s = session_repo.get_session(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return (s.state, s.customer_id)

    try:
        result = await agent.execute_turn(
            prompt=request.prompt,
            session=agent_session,
            state_refresher=_refresh_state,
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from exc

    # Persist transcript. Index 0 is Agent's ephemeral SYSTEM_PROMPT; every
    # other role (including later `system` messages injected by auth.py) is
    # part of the LLM-visible history and must be preserved.
    serialized_messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "tool_call_id": msg.tool_call_id,
            "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls]
            if msg.tool_calls
            else None,
        }
        for msg in result.messages[1:]
    ]
    session_repo.set_conversation_messages(chat_session.id, serialized_messages)

    # Reload session (tools may have mutated it)
    chat_session = session_repo.get_session(chat_session.id) or chat_session

    if not result.reply.strip():
        raise HTTPException(status_code=500, detail="The assistant returned an empty response. Please try again.")

    # Stamp cookies and extend DB TTL on every successful response (rolling window)
    new_expires_at = datetime.now(UTC) + timedelta(seconds=settings.auth_session_ttl_seconds)
    session_repo.touch_session(chat_session.id, new_expires_at)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=str(chat_session.id),
        max_age=settings.auth_session_ttl_seconds,
        **_cookie_attrs_for_request(http_request),
    )
    return ChatResponse(
        reply=result.reply,
        session_id=chat_session.id,
        state=chat_session.state,
        verification_required=chat_session.state == ChatSessionState.CODE_SENT,
    )


@router.get("/session", response_model=SessionRestoreResponse)
def restore_session(
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    session_id: Annotated[UUID | None, Cookie()] = None,
) -> SessionRestoreResponse:
    """Return session state and user/assistant message history for client-side restoration."""
    if session_id is None:
        raise HTTPException(status_code=404, detail="No active session")

    chat_session = session_repo.get_session(session_id)
    if chat_session is None:
        raise SessionExpiredError()

    raw = session_repo.get_conversation_messages(session_id, preloaded=chat_session)
    messages = [
        RestoredMessage(role=m["role"], content=m["content"] or "")
        for m in raw
        if m.get("role") in {"user", "assistant"} and m.get("content")
    ]
    return SessionRestoreResponse(
        session_id=chat_session.id,
        state=chat_session.state,
        verification_required=chat_session.state == ChatSessionState.CODE_SENT,
        messages=messages,
    )
