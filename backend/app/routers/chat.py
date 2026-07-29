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
) -> StreamingResponse:
    pass

   