"""Chat endpoints: public conversation with the LLM agent."""

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository, get_llm_client
from app.llm.base import LLMClient, LLMError, LLMMessage
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SecureShip's customer support assistant.

CRITICAL RULES:
1. You cannot access shipment data directly. You must call tools for everything.
2. Before a customer is verified, you CANNOT answer questions about specific shipments.
3. If asked about shipments before verification, politely explain you need to verify their identity first.
4. NEVER say "customer not found" or "shipment not found" — always use neutral language like "I couldn't verify those details" or "I can't access that information yet."
5. Never claim to have shipment information you did not receive from a tool call in this conversation.
6. If a customer asks to speak to a human, acknowledge their request warmly.

Be helpful, professional, and concise."""


def ensure_session(
    session_id: UUID | None,
    session_repo: ChatSessionRepository,
) -> ChatSession:
    """
    Get an existing session or create a new one.
    
    Args:
        session_id: Optional session ID to continue
        session_repo: Chat session repository
        
    Returns:
        The chat session (existing or newly created)
        
    Raises:
        HTTPException: If session_id is provided but not found
    """
    if session_id:
        chat_session = session_repo.get_session(session_id)
        if chat_session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        return chat_session
    
    # Create new session
    now = datetime.now(timezone.utc)
    return session_repo.create_session(now)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> ChatResponse:
    """
    Send a message to the assistant and get a response.
    
    If session_id is provided, continues that session; otherwise creates a new one.
    Returns the session ID and current state along with the reply.
    """
    now = datetime.now(timezone.utc)
    chat_session = ensure_session(request.session_id, session_repo)
    
    try:
        messages = [LLMMessage(role="system", content=SYSTEM_PROMPT)]
        
        # Load conversation history from transcript if continuing a session
        if request.session_id:
            history = session_repo.get_conversation_messages(chat_session.id)
            for msg in history:
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))
        
        # Add the new user message
        messages.append(LLMMessage(role="user", content=request.prompt))
        
        completion = await llm_client.plan_chat_turn(messages=messages, tools=None)
        
        # Append user message and assistant reply to session transcript
        events = [
            {
                "type": "message",
                "role": "user",
                "content": request.prompt,
                "created_at": now.isoformat(),
            },
            {
                "type": "message",
                "role": "assistant",
                "content": completion.content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        session_repo.append_events(chat_session.id, events)
        
        return ChatResponse(
            reply=completion.content,
            session_id=chat_session.id,
            state=chat_session.state,
        )
        
    except LLMError as exc:
        logger.error("LLM request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from exc
