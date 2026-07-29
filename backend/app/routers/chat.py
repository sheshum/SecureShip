"""Chat endpoint: HTTP/SSE transport only - business logic lives in ChatService.

SSE wire format (one JSON object per `data:` line):
    {"type": "token", "content": "..."}       streamed response fragment
    {"type": "tool_call", ...}                 tool invocation notice
    {"type": "tool_result", ...}               tool result payload
    {"type": "error", "message": "..."}    stream aborted
    {"type": "done"}                           stream finished normally
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_auth_gate_service,
    get_auth_session_store,
    get_chat_service,
    get_chat_session_repository,
)
from app.llm.base import LLMError, LLMMessage
from app.llm.tools import AuthContext
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatContinueRequest, ChatRequest
from app.services.auth_gate import AuthGateService
from app.services.auth_session import AuthSessionStore
from app.services.chat import ChatService
from app.services.chat_streaming import (
    assistant_message_event,
    auth_state_event,
    resolve_auth_gate,
    resolve_or_create_session,
    run_auth_gate_turn,
    session_event,
    sse_event,
    tool_transcript_event,
    user_message_event,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    # Tell reverse proxies (nginx) not to buffer the stream.
    "X-Accel-Buffering": "no",
}


def _conversation_messages_for_session(
    *,
    session_repository: ChatSessionRepository,
    session_id: UUID,
) -> list[LLMMessage]:
    transcript_messages = session_repository.get_conversation_messages(session_id)
    return [
        LLMMessage(role=message["role"], content=message["content"])
        for message in transcript_messages
    ]


async def _stream_assistant_turn(
    *,
    service: ChatService,
    session_repository: ChatSessionRepository,
    session_id,
    messages: list[LLMMessage],
    auth_context: AuthContext,
) -> AsyncIterator[str]:
    assistant_chunks: list[str] = []
    turn_id = f"turn_{uuid4().hex}"

    try:
        async for event in service.agent_stream(
            messages,
            auth_context=auth_context,
        ):
            event_type = event.get("type")

            if event_type == "token":
                assistant_chunks.append(str(event.get("content") or ""))
            elif event_type in {"tool_call", "tool_result"}:
                session_repository.append_events(
                    session_id,
                    [tool_transcript_event(event, turn_id=turn_id)],
                )
            elif event_type == "done":
                assistant_content = "".join(assistant_chunks).strip()
                if assistant_content:
                    session_repository.append_events(
                        session_id,
                        [assistant_message_event(assistant_content, turn_id=turn_id)],
                    )

            yield sse_event(event)

    except asyncio.CancelledError:
        # Client disconnected; intentionally discard partial assistant text.
        raise
    except LLMError as exc:
        yield sse_event({"type": "error", "message": str(exc)})


@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    auth_gate_service: Annotated[AuthGateService, Depends(get_auth_gate_service)],
) -> StreamingResponse:
    current_time = datetime.now(UTC)
    session_context = resolve_or_create_session(
        request.session_id,
        session_repository,
        now=current_time,
    )
    gate = resolve_auth_gate(
        session_context,
        session_repository,
        auth_session_store,
        now=current_time,
    )

    user_message_content = request.prompt.strip()
    if not user_message_content:
        raise HTTPException(status_code=422, detail="Prompt must not be empty.")

    pending_turn_id = f"turn_{uuid4().hex}"
    session_repository.append_events(
        session_context.session_id,
        [
            user_message_event(user_message_content)
            | {"meta": {"source": "ui", "turn_id": pending_turn_id}}
        ],
    )

    messages = _conversation_messages_for_session(
        session_repository=session_repository,
        session_id=session_context.session_id,
    )

    async def stream() -> AsyncIterator[str]:
        yield sse_event(session_event(session_context.session_id))
        yield sse_event(auth_state_event(gate.state, auth_expires_at=gate.auth_expires_at))

        if gate.requires_auth:
            session_repository.set_pending_turn(
                session_context.session_id,
                turn_id=pending_turn_id,
                content=user_message_content,
            )
            async for event in run_auth_gate_turn(
                messages,
                session_id=session_context.session_id,
                turn_id=pending_turn_id,
                should_show_code_modal=gate.should_show_code_modal,
                chat_service=service,
                auth_gate_service=auth_gate_service,
                session_repository=session_repository,
            ):
                yield sse_event(event)
            return

        async for event in _stream_assistant_turn(
            service=service,
            session_repository=session_repository,
            session_id=session_context.session_id,
            messages=messages,
            auth_context=AuthContext(customer_id=gate.verified_customer_id),
        ):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/continue")
async def continue_chat(
    request: ChatContinueRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    auth_gate_service: Annotated[AuthGateService, Depends(get_auth_gate_service)],
) -> StreamingResponse:
    current_time = datetime.now(UTC)
    session_context = resolve_or_create_session(
        request.session_id,
        session_repository,
        now=current_time,
    )
    gate = resolve_auth_gate(
        session_context,
        session_repository,
        auth_session_store,
        now=current_time,
    )

    pending_turn = session_repository.get_pending_turn(session_context.session_id)
    if pending_turn is None:
        raise HTTPException(status_code=409, detail="No pending chat turn to continue.")

    pending_turn_id = str(pending_turn.get("turn_id") or "")
    pending_status = str(pending_turn.get("status") or "pending")

    if pending_turn_id != request.pending_turn_id:
        raise HTTPException(status_code=409, detail="Pending turn does not match request.")

    if pending_status != "pending":
        raise HTTPException(status_code=409, detail="Pending turn is already being processed.")

    messages = _conversation_messages_for_session(
        session_repository=session_repository,
        session_id=session_context.session_id,
    )

    async def stream() -> AsyncIterator[str]:
        yield sse_event(session_event(session_context.session_id))
        yield sse_event(auth_state_event(gate.state, auth_expires_at=gate.auth_expires_at))

        if gate.requires_auth:
            async for event in run_auth_gate_turn(
                messages,
                session_id=session_context.session_id,
                turn_id=pending_turn_id,
                should_show_code_modal=gate.should_show_code_modal,
                chat_service=service,
                auth_gate_service=auth_gate_service,
                session_repository=session_repository,
            ):
                yield sse_event(event)
            return

        session_repository.set_pending_turn_status(
            session_context.session_id,
            status="processing",
        )

        try:
            async for event in _stream_assistant_turn(
                service=service,
                session_repository=session_repository,
                session_id=session_context.session_id,
                messages=messages,
                auth_context=AuthContext(customer_id=gate.verified_customer_id),
            ):
                yield event

            session_repository.clear_pending_turn(session_context.session_id)
        except Exception:
            session_repository.set_pending_turn_status(
                session_context.session_id,
                status="pending",
            )
            raise

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
