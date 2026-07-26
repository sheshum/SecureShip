"""Chat endpoint: HTTP/SSE transport only — business logic lives in ChatService.

SSE wire format (one JSON object per `data:` line):
    {"type": "token", "content": "..."}     streamed response fragment
    {"type": "tool_call", ...}                tool invocation notice
    {"type": "tool_result", ...}              tool result payload
    {"type": "error", "message": "..."}     stream aborted
    {"type": "done"}                          stream finished normally
"""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service, get_chat_session_repository
from app.llm.base import LLMError, LLMMessage
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    # Tell reverse proxies (nginx) not to buffer the stream.
    "X-Accel-Buffering": "no",
}


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _new_event_id() -> str:
    return f"evt_{uuid4().hex}"


@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
) -> StreamingResponse:
    chat_session = session_repository.get_session(request.session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = request.messages[-1]
    user_event = {
        "id": _new_event_id(),
        "type": "message",
        "role": "user",
        "content": user_message.content,
        "created_at": _utc_now_iso(),
        "meta": {"source": "ui"},
    }
    session_repository.append_events(request.session_id, [user_event])

    messages = [LLMMessage(role=m.role, content=m.content) for m in request.messages]

    async def stream() -> AsyncIterator[str]:
        assistant_chunks: list[str] = []
        turn_id = f"turn_{uuid4().hex}"

        try:
            async for event in service.agent_stream(messages):
                event_type = event.get("type")

                if event_type == "token":
                    assistant_chunks.append(str(event.get("content") or ""))
                elif event_type in {"tool_call", "tool_result"}:
                    tool_event = {
                        "id": _new_event_id(),
                        "type": event_type,
                        "created_at": _utc_now_iso(),
                        "meta": {"turn_id": turn_id},
                    }
                    if event_type == "tool_call":
                        tool_event["tool"] = event.get("tool")
                        tool_event["args"] = event.get("args")
                    else:
                        tool_event["tool"] = event.get("tool")
                        tool_event["result"] = event.get("result")
                    session_repository.append_events(request.session_id, [tool_event])
                elif event_type == "done":
                    assistant_content = "".join(assistant_chunks).strip()
                    if assistant_content:
                        assistant_event = {
                            "id": _new_event_id(),
                            "type": "message",
                            "role": "assistant",
                            "content": assistant_content,
                            "created_at": _utc_now_iso(),
                            "meta": {"turn_id": turn_id, "finish_reason": "done"},
                        }
                        session_repository.append_events(
                            request.session_id, [assistant_event]
                        )

                yield _sse_event(event)

        except asyncio.CancelledError:
            # Client disconnected; intentionally discard partial assistant text.
            raise
        except LLMError as exc:
            yield _sse_event({"type": "error", "message": str(exc)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
