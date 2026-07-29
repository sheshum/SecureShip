"""Chat endpoints: public conversation with the LLM agent."""

import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository, get_llm_client, get_tool_registry
from app.llm.base import LLMClient, LLMError, LLMMessage
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.sessions import ChatSessionState
from app.services.dispatch import dispatch_tool_call
from app.tools.utils import log_console

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = """You are SecureShip's customer support assistant.
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
    tool_registry: Annotated[dict, Depends(get_tool_registry)],
) -> ChatResponse:
    now = datetime.now(timezone.utc)
    chat_session = ensure_session(request.session_id, session_repo)
    
    try:
        messages = [LLMMessage(role="system", content=SYSTEM_PROMPT)]

        if request.session_id:
            history = session_repo.get_conversation_messages(chat_session.id)
            for msg in history:
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))
        
        messages.append(LLMMessage(role="user", content=request.prompt))

        available_tools = [t.schema for t in tool_registry.values()]

        # Agentic loop: keep calling LLM until no more tool calls
        while True:
            # Call LLM with current message history and available tools
            completion = await llm_client.plan_chat_turn(
                messages=messages,
                tools=available_tools if available_tools else None
            )
            
            # Log LLM response
            log_console("LLM Response", {
                "has_tool_calls": bool(completion.tool_calls),
                "content_preview": completion.content[:100] if completion.content else None
            })
            
            # Add assistant's message to conversation history
            messages.append(LLMMessage(
                role="assistant",
                content=completion.content or "",
                tool_calls=completion.tool_calls
            ))
            
            # If no tool calls, we have the final response
            if not completion.tool_calls:
                break
            
            # Log tool calls
            log_console("Tool Calls", [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in completion.tool_calls
            ])
            
            # Execute each tool call
            for tool_call in completion.tool_calls:
                # Parse tool arguments
                try:
                    tool_args = json.loads(tool_call.arguments)
                except json.JSONDecodeError:
                    tool_args = {}
                
                # Dispatch tool call (enforces verification gate)
                tool_result = await dispatch_tool_call(
                    session=chat_session,
                    fn_name=tool_call.name,
                    args=tool_args,
                    tool_registry=tool_registry,
                )
                
                # Log tool result
                log_console(f"Tool Result: {tool_call.name}", tool_result)
                
                # Add tool result to message history
                messages.append(LLMMessage(
                    role="tool",
                    content=json.dumps(tool_result),
                    tool_call_id=tool_call.id
                ))
            
            # Reload session to get any state changes from tools
            chat_session = session_repo.get_session(chat_session.id) or chat_session
        
        # Save conversation messages to transcript (excluding system prompt)
        serialized_messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_call_id": msg.tool_call_id,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in msg.tool_calls
                ] if msg.tool_calls else None,
            }
            for msg in messages[1:]  # Skip system prompt
        ]
        session_repo.set_conversation_messages(chat_session.id, serialized_messages)
        
        return ChatResponse(
            reply=completion.content,
            session_id=chat_session.id,
            state=chat_session.state,
            verification_required=chat_session.state == ChatSessionState.CODE_SENT,
        )
        
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from exc
