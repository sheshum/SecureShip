"""Chat endpoints: public conversation with the LLM agent."""

import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository, get_llm_client, get_tool_registry
from app.llm.base import LLMClient, LLMError, LLMMessage
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.sessions import ChatSessionState
from app.services.auth_context import AuthContext
from app.services.dispatch import dispatch_tool_call
from app.tools.utils import log_console

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = """You are SecureShip's customer support assistant.
Your role is to help customers with questions about their shipments, tracking, and deliveries.
Be helpful, professional, and concise. If you don't know something, say so instead of guessing.

# General Guidelines:
- Try to resolve the customer's issue in a single response, but you can ask for more information if needed.
- Try to resolve the issue by yourself before escalating to a human agent. If you must escalate, provide a clear explanation of the issue and any relevant details.
- Be concise and clear in your responses.

# Workflow:
- If the customer is unverified, you must first verify their identity using the verify_identity tool. Do not provide any shipment information until the customer is verified.
- When processing a request, first assess the complexity of the request.
- Break complex requests into smaller steps and resolve them one at a time.


# Escalate to Human - request examples:

1. Customer: "I want to talk to a human"

Explanation: Explicit request to escalate to a human agent. Use the escalate_to_human tool.

2. Customer: "My package is lost and I need a refund"

Explanation: The customer reports a lost package and requests a refund. Use the escalate_to_human tool.



# Constraints:
- **NEVER** provide shipment information for a customer who is not verified.
- **NEVER** include personally identifiable information (PII) in your responses.

"""


def ensure_session(
    session_id: UUID | None,
    session_repo: ChatSessionRepository,
) -> ChatSession:
    """Get an existing session or create a new one.

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
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return chat_session

    now = datetime.now(UTC)
    return session_repo.create_session(now)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    tool_registry: Annotated[dict, Depends(get_tool_registry)],
) -> ChatResponse:
    chat_session = ensure_session(request.session_id, session_repo)

    auth_context = AuthContext(
        session_id=chat_session.id,
        customer_id=chat_session.customer_id,
        state=chat_session.state,
    )

    # Force verify_identity tool for unverified sessions
    tool_choice = ["verify_identity"] if auth_context.state != ChatSessionState.VERIFIED else None

    try:
        messages = [LLMMessage(role="system", content=SYSTEM_PROMPT)]

        if request.session_id:
            history = session_repo.get_conversation_messages(chat_session.id)
            for msg in history:
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        messages.append(LLMMessage(role="user", content=request.prompt))

        available_tools = [t.schema for t in tool_registry.values()]

        while True:
            completion = await llm_client.plan_chat_turn(
                messages=messages,
                tools=available_tools if available_tools else None,
                tool_choice=tool_choice,
            )

            log_console(
                "LLM Response",
                {
                    "has_tool_calls": bool(completion.tool_calls),
                    "content_preview": completion.content[:100] if completion.content else None,
                },
            )

            messages.append(
                LLMMessage(
                    role="assistant",
                    content=completion.content or "",
                    tool_calls=completion.tool_calls,
                )
            )

            if not completion.tool_calls:
                break

            # Log tool calls
            log_console(
                "Tool Calls",
                [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in completion.tool_calls
                ],
            )

            for tool_call in completion.tool_calls:
                try:
                    tool_args = json.loads(tool_call.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                # Dispatch tool call (enforces verification gate)
                tool_result = await dispatch_tool_call(
                    context=auth_context,
                    fn_name=tool_call.name,
                    args=tool_args,
                    tool_registry=tool_registry,
                )

                # Log tool result
                log_console(f"Tool Result: {tool_call.name}", tool_result)

                messages.append(
                    LLMMessage(
                        role="tool", content=json.dumps(tool_result), tool_call_id=tool_call.id
                    )
                )

            chat_session = session_repo.get_session(chat_session.id) or chat_session

        serialized_messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_call_id": msg.tool_call_id,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in msg.tool_calls
                ]
                if msg.tool_calls
                else None,
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
