"""Chat endpoint: HTTP/SSE transport only — business logic lives in ChatService.

SSE wire format (one JSON object per `data:` line):
    {"type": "token", "content": "..."}     streamed response fragment
    {"type": "tool_call", ...}                tool invocation notice
    {"type": "tool_result", ...}              tool result payload
    {"type": "error", "message": "..."}     stream aborted
    {"type": "done"}                          stream finished normally
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_auth_session_store,
    get_chat_service,
    get_chat_session_repository,
)
from app.llm.base import LLMError, LLMMessage
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest
from app.services.auth_session import AuthSessionStore
from app.services.chat import ChatService
from app.llm.tools import AuthContext
from app.services.chat_streaming import (
    assistant_message_event,
    auth_required_event,
    auth_state_event,
    done_event,
    resolve_auth_gate,
    resolve_or_create_session,
    session_event,
    show_code_modal_event,
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
@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
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

    user_message = request.messages[-1]
    session_repository.append_events(
        session_context.session_id,
        [user_message_event(user_message.content)],
    )

    messages = [LLMMessage(role=m.role, content=m.content) for m in request.messages]

    async def stream() -> AsyncIterator[str]:
        assistant_chunks: list[str] = []
        turn_id = f"turn_{uuid4().hex}"

        try:
            yield sse_event(session_event(session_context.session_id))

            yield sse_event(auth_state_event(gate.state, auth_expires_at=gate.auth_expires_at))

            if gate.requires_auth:
                if gate.should_show_code_modal:
                    yield sse_event(show_code_modal_event())
                yield sse_event(auth_required_event())
                yield sse_event(done_event())
                return

            async for event in service.agent_stream(
                messages,
                auth_context=AuthContext(customer_id=gate.verified_customer_id),
            ):
                event_type = event.get("type")

                if event_type == "token":
                    assistant_chunks.append(str(event.get("content") or ""))
                elif event_type in {"tool_call", "tool_result"}:
                    session_repository.append_events(
                        session_context.session_id,
                        [tool_transcript_event(event, turn_id=turn_id)],
                    )
                elif event_type == "done":
                    assistant_content = "".join(assistant_chunks).strip()
                    if assistant_content:
                        session_repository.append_events(
                            session_context.session_id,
                            [assistant_message_event(assistant_content, turn_id=turn_id)],
                        )

                yield sse_event(event)

        except asyncio.CancelledError:
            # Client disconnected; intentionally discard partial assistant text.
            raise
        except LLMError as exc:
            yield sse_event({"type": "error", "message": str(exc)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
