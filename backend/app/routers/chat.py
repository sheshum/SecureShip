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
        # SEC-9: Privacy-aware system prompt — never leaks enumeration info
        system_prompt = """You are SecureShip's customer support assistant.

CRITICAL RULES:
1. You cannot access shipment data directly. You must call tools for everything.
2. Before a customer is verified, you CANNOT answer questions about specific shipments.
3. If asked about shipments before verification, politely explain you need to verify their identity first.
4. NEVER say "customer not found" or "shipment not found" — always use neutral language like "I couldn't verify those details" or "I can't access that information yet."
5. Never claim to have shipment information you did not receive from a tool call in this conversation.
6. If a customer asks to speak to a human, acknowledge their request warmly.

Be helpful, professional, and concise."""

        messages = [
            LLMMessage(role="system", content=system_prompt),
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
