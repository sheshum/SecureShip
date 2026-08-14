"""Agent: orchestrates agentic loop over LLM + tools."""

import json
from typing import Any

from app.agent.prompts import get_system_prompt
from app.agent.result import AgentResult
from app.agent.session import AgentSession, SessionStateRefresher
from app.llm.base import LLMClient, LLMMessage, ToolCall
from app.schemas.sessions import ChatSessionState
from app.services.auth_context import AuthContext
from app.services.dispatch import dispatch_tool_call
from app.tools.tool_registry import ToolName, ToolRegistry
from app.tools.utils import log_console

# Hard ceiling on tool-call iterations per turn. Identity -> verify -> lookup
# -> answer is at most 3-4 hops; anything past this is a runaway loop.
MAX_ITERATIONS = 6


class Agent:
    """Orchestrates multi-turn agentic loop: LLM → tool calls → dispatch → repeat.

    Responsibilities:
    - Message list construction (system prompt + history + new user message)
    - Tool choice logic (conditional forcing of verify_identity)
    - Agentic loop execution

    Does NOT:
    - Access database (no session_repo dependency)
    - Authorize tool access (that's dispatch_tool_call's job)
    - Persist session state (caller's responsibility)
    - Validate requests (that's the router's job)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry

    def _resolve_available_tools(self, session_state: ChatSessionState) -> list[dict[str, Any]]:
        """Tool schemas the model may see for this state.

        Invariant: any tool with requires_verification=True is only exposed when
        state == VERIFIED. Intermediate states (CODE_SENT / AWAITING_CODE) expose
        only escalate so the model doesn't waste a turn calling a gated tool.
        """
        if session_state == ChatSessionState.ANONYMOUS:
            return [
                self.tool_registry.require(ToolName.REQUEST_IDENTITY_INFO).schema,
                self.tool_registry.require(ToolName.ESCALATE_TO_HUMAN).schema,
            ]
        if session_state == ChatSessionState.COLLECTING_IDENTITY:
            return [
                self.tool_registry.require(ToolName.START_IDENTITY_VERIFICATION).schema,
                self.tool_registry.require(ToolName.ESCALATE_TO_HUMAN).schema,
            ]
        if session_state in {
            ChatSessionState.CODE_SENT,
            ChatSessionState.AWAITING_CODE,
        }:
            # Waiting on the OTP UI; nothing useful the model can do except escalate.
            return [self.tool_registry.require(ToolName.ESCALATE_TO_HUMAN).schema]
        if session_state == ChatSessionState.CODE_EXPIRED:
            return [
                self.tool_registry.require(ToolName.REQUEST_IDENTITY_INFO).schema,
                self.tool_registry.require(ToolName.ESCALATE_TO_HUMAN).schema,
            ]
        if session_state == ChatSessionState.VERIFIED:
            return [
                self.tool_registry.require(ToolName.LOOKUP_SHIPMENTS).schema,
                self.tool_registry.require(ToolName.ESCALATE_TO_HUMAN).schema,
            ]
        # ESCALATED_TO_HUMAN and any future terminal states.
        return []

    @staticmethod
    def _resolve_tool_choice(session_state: ChatSessionState, *, is_first_iteration: bool) -> str:
        """Force a tool call on the first LLM call for gated states.

        Uses "required" (not a specific tool) so the model can still pick
        escalate_to_human from the exposed list if the user asks for one.
        Subsequent iterations use "auto" so the model can respond after
        consuming the tool's result rather than re-invoking it.
        """
        if not is_first_iteration:
            return "auto"
        if session_state in {
            ChatSessionState.ANONYMOUS,
            ChatSessionState.COLLECTING_IDENTITY,
        }:
            return "required"
        return "auto"

    def _build_messages(self, session: AgentSession, prompt: str) -> list[LLMMessage]:
        messages: list[LLMMessage] = [LLMMessage(role="system", content=get_system_prompt(session.state))]
        for msg in session.history:
            raw_tool_calls = msg.get("tool_calls") or ()
            tool_calls = tuple(
                ToolCall(
                    id=str(tc.get("id", "")),
                    name=str(tc.get("name", "")),
                    arguments=str(tc.get("arguments", "")),
                )
                for tc in raw_tool_calls
                if isinstance(tc, dict)
            )
            messages.append(
                LLMMessage(
                    role=msg["role"],
                    content=msg.get("content") or "",
                    tool_call_id=msg.get("tool_call_id"),
                    tool_calls=tool_calls,
                )
            )
        messages.append(LLMMessage(role="user", content=prompt))
        return messages

    async def execute_turn(
        self,
        prompt: str,
        session: AgentSession,
        state_refresher: SessionStateRefresher,
    ) -> AgentResult:
        """Execute one conversational turn with agentic loop.

        Args:
            prompt: User's message
            session: Immutable session snapshot (state, history, etc.)
            state_refresher: Callable that returns fresh (state, customer_id) from the store.

        Returns:
            AgentResult with final reply and full message list

        Raises:
            LLMError: If LLM client fails
        """
        # Build auth context from session
        auth_context = AuthContext(
            session_id=session.session_id,
            customer_id=session.customer_id,
            state=session.state,
        )

        current_state = session.state
        available_tools = self._resolve_available_tools(current_state)
        messages = self._build_messages(session, prompt)
        tool_calls_made = 0
        completion = None

        for iteration in range(MAX_ITERATIONS):
            tool_choice = self._resolve_tool_choice(current_state, is_first_iteration=iteration == 0)
            log_console(
                "Agent Turn",
                {
                    "session_id": str(session.session_id),
                    "customer_id": auth_context.customer_id,
                    "state": current_state,
                    "iteration": iteration,
                    "messages_count": len(messages),
                    "tool_choice": tool_choice,
                    "available_tools": [t.get("function", {}).get("name") for t in available_tools],
                },
            )
            completion = await self.llm_client.plan_chat_turn(
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
                break  # Done - no more tool calls

            log_console(
                "Tool Calls",
                [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in completion.tool_calls],
            )

            for tool_call in completion.tool_calls:
                tool_calls_made += 1
                try:
                    tool_args = json.loads(tool_call.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                tool_result = await dispatch_tool_call(
                    context=auth_context,
                    fn_name=tool_call.name,
                    args=tool_args,
                    tool_registry=self.tool_registry,
                )

                log_console(f"Tool Result: {tool_call.name}", tool_result)

                messages.append(
                    LLMMessage(
                        role="tool",
                        content=json.dumps(tool_result),
                        tool_call_id=tool_call.id,
                    )
                )

            fresh_state, fresh_customer_id = await state_refresher(session.session_id)
            auth_context = AuthContext(
                session_id=session.session_id,
                customer_id=fresh_customer_id,
                state=fresh_state,
            )
            current_state = fresh_state
            available_tools = self._resolve_available_tools(fresh_state)
        else:
            # Loop exhausted without a terminal (tool-call-free) response.
            log_console(
                "Agent loop exhausted",
                {"session_id": str(session.session_id), "iterations": MAX_ITERATIONS},
            )
            return AgentResult(
                reply="Sorry, I couldn't complete that request. Please try again.",
                messages=messages,
                tool_calls_made=tool_calls_made,
            )

        return AgentResult(
            reply=(completion.content if completion else "") or "",
            messages=messages,
            tool_calls_made=tool_calls_made,
        )
