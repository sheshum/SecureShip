"""Chat endpoints: public conversation with the LLM agent."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.agent import Agent, AgentSession
from app.agent.prompts import ESCALATION_NOTE
from app.dependencies import get_agent, get_chat_session_repository, get_customer_repository
from app.llm.base import LLMError
from app.models import ChatSession
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.sessions import ChatSessionState

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
    agent: Annotated[Agent, Depends(get_agent)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> ChatResponse:
    """Chat endpoint: delegate to Agent for agentic loop execution."""
    # 1. Load session from DB
    chat_session = ensure_session(request.session_id, session_repo)
    pre_agent_state = chat_session.state

    # 2. Build agent session (snapshot of current state)
    agent_session = AgentSession(
        session_id=chat_session.id,
        customer_id=chat_session.customer_id,
        state=chat_session.state,
        history=session_repo.get_conversation_messages(chat_session.id),
    )

    # 3. Execute agent turn (pure orchestration, no DB)
    async def _refresh_state(session_id: UUID) -> tuple[ChatSessionState, int | None]:
        s = session_repo.get_session(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return (s.state, s.customer_id)

    try:
        result = await agent.execute_turn(
            prompt=request.prompt,
            session=agent_session,
            state_refresher=_refresh_state,
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from exc

    # 4. Persist transcript. Index 0 is Agent's ephemeral SYSTEM_PROMPT; every
    # other role (including later `system` messages injected by auth.py) is
    # part of the LLM-visible history and must be preserved.
    serialized_messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "tool_call_id": msg.tool_call_id,
            "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls]
            if msg.tool_calls
            else None,
        }
        for msg in result.messages[1:]
    ]
    session_repo.set_conversation_messages(chat_session.id, serialized_messages)

    # 5. Reload session (tools may have mutated it)
    chat_session = session_repo.get_session(chat_session.id) or chat_session

    # 6. Detect if escalation happened this turn and inject the Melany persona note.
    escalation_handoff = (
        pre_agent_state != ChatSessionState.ESCALATED_TO_HUMAN
        and chat_session.state == ChatSessionState.ESCALATED_TO_HUMAN
    )
    if escalation_handoff:
        session_repo.append_messages(
            chat_session.id,
            [{"role": "system", "content": ESCALATION_NOTE, "tool_call_id": None, "tool_calls": None}],
        )

    # 7. Resolve verified customer's first name for the personalised Melany greeting.
    customer_first_name: str | None = None
    if chat_session.customer_id is not None:
        customer = customer_repo.get_customer_by_id(chat_session.customer_id)
        if customer is not None:
            customer_first_name = customer.get("first_name")

    # 8. Build response with fresh state
    return ChatResponse(
        reply=result.reply,
        session_id=chat_session.id,
        state=chat_session.state,
        verification_required=chat_session.state == ChatSessionState.CODE_SENT,
        escalation_handoff=escalation_handoff,
        customer_first_name=customer_first_name,
    )
