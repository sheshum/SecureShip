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
    get_auth_session_store,
    get_chat_service,
    get_chat_session_repository,
    get_identity_verification_service,
    get_otp_service,
    get_sms_service,
)
from app.llm.base import LLMError, LLMMessage
from app.llm.tools import AuthContext
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.chat import ChatContinueRequest, ChatRequest
from app.services.auth_session import AuthSessionStore
from app.services.chat import ChatService
from app.services.identity_verification import IdentityVerificationService
from app.services.otp import OtpService
from app.services.sms import SmsService
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


def _execute_auth_gate_tool_call(
    *,
    tool_name: str,
    tool_args: dict,
    session_id: UUID,
    session_repository: ChatSessionRepository,
    identity_service: IdentityVerificationService,
    otp_service: OtpService,
    sms_service: SmsService,
) -> dict:
    if tool_name == "request_identity_info":
        return {
            "ok": True,
            "action": "collect_identity",
            "required_fields": ["first_name", "last_name", "phone_number"],
            "message": "Please share your first name, last name, and phone number so I can verify your identity.",
        }

    if tool_name != "verify_identity":
        return {
            "ok": False,
            "error": f"Unknown tool: {tool_name}",
        }

    first_name = str(tool_args.get("first_name") or "").strip()
    last_name = str(tool_args.get("last_name") or "").strip()
    phone_number = str(tool_args.get("phone_number") or "").strip()

    if not first_name or not last_name or not phone_number:
        return {
            "ok": False,
            "started": False,
            "show_code_modal": False,
            "state": "collecting_identity",
            "message": "I still need first name, last name, and phone number to verify your identity.",
            "error_code": "missing_identity_fields",
        }

    identity = identity_service.verify_identity(
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    if not identity.matched or identity.match is None:
        session_repository.update_auth_state(
            session_id,
            state="collecting_identity",
            customer_id=None,
        )
        return {
            "ok": False,
            "started": False,
            "show_code_modal": False,
            "state": "collecting_identity",
            "message": "We could not verify your identity. Please check your details and try again.",
            "error_code": "identity_no_match",
        }

    pending_customer_id = UUID(identity.match.customer_id)
    otp_issue = otp_service.issue_code(
        session_id,
        pending_customer_id=pending_customer_id,
    )
    if not otp_issue.ok:
        return {
            "ok": False,
            "started": False,
            "show_code_modal": False,
            "state": "awaiting_code",
            "message": "Please wait before requesting another verification code.",
            "error_code": otp_issue.error_code,
            "retry_at": (
                otp_issue.retry_at.isoformat().replace("+00:00", "Z")
                if otp_issue.retry_at is not None
                else None
            ),
        }

    sms_service.send_otp(phone_number, otp_issue.otp_code or "")
    session_repository.update_auth_state(
        session_id,
        state="code_sent",
        customer_id=None,
    )

    return {
        "ok": True,
        "started": True,
        "show_code_modal": True,
        "state": "code_sent",
        "message": "Verification code sent. Enter the code to continue.",
    }


def _conversation_messages_for_session(
    *,
    session_repository: ChatSessionRepository,
    session_id: UUID,
) -> list[LLMMessage]:
    transcript_messages = session_repository.get_conversation_messages(session_id)
    return [
        LLMMessage(role=message["role"], content=message["content"])
        for message in transcript_messages
    ]


async def _stream_assistant_turn(
    *,
    service: ChatService,
    session_repository: ChatSessionRepository,
    session_id,
    messages: list[LLMMessage],
    auth_context: AuthContext,
) -> AsyncIterator[str]:
    assistant_chunks: list[str] = []
    turn_id = f"turn_{uuid4().hex}"

    try:
        async for event in service.agent_stream(
            messages,
            auth_context=auth_context,
        ):
            event_type = event.get("type")

            if event_type == "token":
                assistant_chunks.append(str(event.get("content") or ""))
            elif event_type in {"tool_call", "tool_result"}:
                session_repository.append_events(
                    session_id,
                    [tool_transcript_event(event, turn_id=turn_id)],
                )
            elif event_type == "done":
                assistant_content = "".join(assistant_chunks).strip()
                if assistant_content:
                    session_repository.append_events(
                        session_id,
                        [assistant_message_event(assistant_content, turn_id=turn_id)],
                    )

            yield sse_event(event)

    except asyncio.CancelledError:
        # Client disconnected; intentionally discard partial assistant text.
        raise
    except LLMError as exc:
        yield sse_event({"type": "error", "message": str(exc)})


@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    identity_service: Annotated[
        IdentityVerificationService, Depends(get_identity_verification_service)
    ],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    sms_service: Annotated[SmsService, Depends(get_sms_service)],
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

    user_message_content = request.prompt.strip()
    if not user_message_content:
        raise HTTPException(status_code=422, detail="Prompt must not be empty.")

    pending_turn_id = f"turn_{uuid4().hex}"
    session_repository.append_events(
        session_context.session_id,
        [
            user_message_event(user_message_content)
            | {"meta": {"source": "ui", "turn_id": pending_turn_id}}
        ],
    )

    messages = _conversation_messages_for_session(
        session_repository=session_repository,
        session_id=session_context.session_id,
    )

    async def stream() -> AsyncIterator[str]:
        yield sse_event(session_event(session_context.session_id))
        yield sse_event(auth_state_event(gate.state, auth_expires_at=gate.auth_expires_at))

        if gate.requires_auth:
            existing_pending_turn = session_repository.get_pending_turn(session_context.session_id)
            active_pending_turn_id = pending_turn_id
            if isinstance(existing_pending_turn, dict) and str(existing_pending_turn.get("status") or "") == "pending":
                existing_turn_id = str(existing_pending_turn.get("turn_id") or "").strip()
                if existing_turn_id:
                    active_pending_turn_id = existing_turn_id
            else:
                session_repository.set_pending_turn(
                    session_context.session_id,
                    turn_id=pending_turn_id,
                    content=user_message_content,
                )

            auth_prompt_message = None
            should_open_code_modal = False
            async for auth_event in service.auth_gate_stream(messages):
                if auth_event.get("type") == "tool_call":
                    tool_name = str(auth_event.get("tool") or "")
                    tool_args = auth_event.get("args")
                    if not isinstance(tool_args, dict):
                        tool_args = {}

                    session_repository.append_events(
                        session_context.session_id,
                        [tool_transcript_event(auth_event, turn_id=active_pending_turn_id)],
                    )
                    yield sse_event(auth_event)

                    tool_result = _execute_auth_gate_tool_call(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        session_id=session_context.session_id,
                        session_repository=session_repository,
                        identity_service=identity_service,
                        otp_service=otp_service,
                        sms_service=sms_service,
                    )
                    tool_result_event = {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": tool_result,
                    }
                    session_repository.append_events(
                        session_context.session_id,
                        [tool_transcript_event(tool_result_event, turn_id=active_pending_turn_id)],
                    )
                    yield sse_event(tool_result_event)

                    if isinstance(tool_result.get("message"), str):
                        auth_prompt_message = str(tool_result.get("message"))
                    should_open_code_modal = bool(tool_result.get("show_code_modal"))
                elif auth_event.get("type") == "auth_required":
                    auth_prompt_message = str(auth_event.get("message") or "")

            if should_open_code_modal or gate.should_show_code_modal:
                yield sse_event(show_code_modal_event())
            yield sse_event(
                auth_required_event(
                    pending_turn_id=active_pending_turn_id,
                    message=auth_prompt_message,
                )
            )
            yield sse_event(done_event())
            return

        async for event in _stream_assistant_turn(
            service=service,
            session_repository=session_repository,
            session_id=session_context.session_id,
            messages=messages,
            auth_context=AuthContext(customer_id=gate.verified_customer_id),
        ):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/continue")
async def continue_chat(
    request: ChatContinueRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_repository: Annotated[
        ChatSessionRepository, Depends(get_chat_session_repository)
    ],
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    identity_service: Annotated[
        IdentityVerificationService, Depends(get_identity_verification_service)
    ],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    sms_service: Annotated[SmsService, Depends(get_sms_service)],
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

    pending_turn = session_repository.get_pending_turn(session_context.session_id)
    if pending_turn is None:
        raise HTTPException(status_code=409, detail="No pending chat turn to continue.")

    pending_turn_id = str(pending_turn.get("turn_id") or "")
    pending_status = str(pending_turn.get("status") or "pending")

    if pending_turn_id != request.pending_turn_id:
        raise HTTPException(status_code=409, detail="Pending turn does not match request.")

    if pending_status != "pending":
        raise HTTPException(status_code=409, detail="Pending turn is already being processed.")

    messages = _conversation_messages_for_session(
        session_repository=session_repository,
        session_id=session_context.session_id,
    )

    async def stream() -> AsyncIterator[str]:
        yield sse_event(session_event(session_context.session_id))
        yield sse_event(auth_state_event(gate.state, auth_expires_at=gate.auth_expires_at))

        if gate.requires_auth:
            auth_prompt_message = None
            should_open_code_modal = False
            async for auth_event in service.auth_gate_stream(messages):
                if auth_event.get("type") == "tool_call":
                    tool_name = str(auth_event.get("tool") or "")
                    tool_args = auth_event.get("args")
                    if not isinstance(tool_args, dict):
                        tool_args = {}

                    session_repository.append_events(
                        session_context.session_id,
                        [tool_transcript_event(auth_event, turn_id=pending_turn_id)],
                    )
                    yield sse_event(auth_event)

                    tool_result = _execute_auth_gate_tool_call(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        session_id=session_context.session_id,
                        session_repository=session_repository,
                        identity_service=identity_service,
                        otp_service=otp_service,
                        sms_service=sms_service,
                    )
                    tool_result_event = {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": tool_result,
                    }
                    session_repository.append_events(
                        session_context.session_id,
                        [tool_transcript_event(tool_result_event, turn_id=pending_turn_id)],
                    )
                    yield sse_event(tool_result_event)

                    if isinstance(tool_result.get("message"), str):
                        auth_prompt_message = str(tool_result.get("message"))
                    should_open_code_modal = bool(tool_result.get("show_code_modal"))
                elif auth_event.get("type") == "auth_required":
                    auth_prompt_message = str(auth_event.get("message") or "")

            if should_open_code_modal or gate.should_show_code_modal:
                yield sse_event(show_code_modal_event())
            yield sse_event(
                auth_required_event(
                    pending_turn_id=pending_turn_id,
                    message=auth_prompt_message,
                )
            )
            yield sse_event(done_event())
            return

        session_repository.set_pending_turn_status(
            session_context.session_id,
            status="processing",
        )

        try:
            async for event in _stream_assistant_turn(
                service=service,
                session_repository=session_repository,
                session_id=session_context.session_id,
                messages=messages,
                auth_context=AuthContext(customer_id=gate.verified_customer_id),
            ):
                yield event

            session_repository.clear_pending_turn(session_context.session_id)
        except Exception:
            session_repository.set_pending_turn_status(
                session_context.session_id,
                status="pending",
            )
            raise

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
