"""Agent: orchestrates agentic loop over LLM + tools."""

import json

from app.agent.result import AgentResult
from app.agent.session import AgentSession
from app.llm.base import LLMClient, LLMMessage
from app.schemas.sessions import ChatSessionState
from app.services.auth_context import AuthContext
from app.services.dispatch import dispatch_tool_call
from app.tools.tool_registry import ToolSpec
from app.tools.utils import log_console


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
        tool_registry: dict[str, ToolSpec],
        system_prompt: str,
    ):
        """Initialize agent with LLM client and tool registry.

        Args:
            llm_client: LLM client for completions
            tool_registry: Available tools (name -> ToolSpec)
            system_prompt: System prompt for the agent
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt

    async def execute_turn(
        self,
        prompt: str,
        session: AgentSession,
    ) -> AgentResult:
        """Execute one conversational turn with agentic loop.

        Args:
            prompt: User's message
            session: Immutable session snapshot (state, history, etc.)

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

        # Force verify_identity tool for unverified sessions
        tool_choice = (
            ["verify_identity"]
            if session.state != ChatSessionState.VERIFIED
            else None
        )

        # Construct message list: system + history + new user message
        messages = [LLMMessage(role="system", content=self.system_prompt)]

        for msg in session.history:
            messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        messages.append(LLMMessage(role="user", content=prompt))

        available_tools = [t.schema for t in self.tool_registry.values()]
        tool_calls_made = 0

        # Agentic loop: LLM → tool calls → dispatch → repeat
        while True:
            completion = await self.llm_client.plan_chat_turn(
                messages=messages,
                tools=available_tools if available_tools else None,
                tool_choice=tool_choice,
            )

            log_console(
                "LLM Response",
                {
                    "has_tool_calls": bool(completion.tool_calls),
                    "content_preview": completion.content[:100]
                    if completion.content
                    else None,
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

            # Log tool calls
            log_console(
                "Tool Calls",
                [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in completion.tool_calls
                ],
            )

            # Execute tool calls
            for tool_call in completion.tool_calls:
                tool_calls_made += 1
                try:
                    tool_args = json.loads(tool_call.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                # Dispatch tool call (enforces verification gate)
                tool_result = await dispatch_tool_call(
                    context=auth_context,
                    fn_name=tool_call.name,
                    args=tool_args,
                    tool_registry=self.tool_registry,
                )

                # Log tool result
                log_console(f"Tool Result: {tool_call.name}", tool_result)

                messages.append(
                    LLMMessage(
                        role="tool",
                        content=json.dumps(tool_result),
                        tool_call_id=tool_call.id,
                    )
                )

        return AgentResult(
            reply=completion.content or "",
            messages=messages,
            tool_calls_made=tool_calls_made,
        )
