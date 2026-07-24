"""Chat endpoint: HTTP/SSE transport only — business logic lives in ChatService.

SSE wire format (one JSON object per `data:` line):
  {"type": "delta", "content": "..."}   streamed response fragment
  {"type": "error", "message": "..."}   stream aborted
  {"type": "done"}                      stream finished normally
"""

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service
from app.llm.base import LLMError, LLMMessage
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


async def _event_stream(
    service: ChatService, messages: list[LLMMessage]
) -> AsyncIterator[str]:
    try:
        async for delta in service.stream_reply(messages):
            yield _sse_event({"type": "delta", "content": delta})
    except LLMError as exc:
        yield _sse_event({"type": "error", "message": str(exc)})
        return
    yield _sse_event({"type": "done"})


@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    messages = [LLMMessage(role=m.role, content=m.content) for m in request.messages]
    return StreamingResponse(
        _event_stream(service, messages),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
