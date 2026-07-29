"""Chat endpoints: public conversation with the LLM agent."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_llm_client
from app.llm.base import LLMClient, LLMError, LLMMessage
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> ChatResponse:
    """
    Send a message to the assistant and get a response.
    
    SEC-7: Basic proxy to Ollama, no tools, no session tracking yet.
    """
    try:
        # Build simple conversation with system prompt and user message
        messages = [
            LLMMessage(
                role="system",
                content="You are a helpful SecureShip customer support assistant.",
            ),
            LLMMessage(role="user", content=request.prompt),
        ]
        
        completion = await llm_client.plan_chat_turn(messages=messages, tools=None)
        
        return ChatResponse(reply=completion.content)
        
    except LLMError as exc:
        logger.error("LLM request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from exc
