"""Chat business logic. Depends only on the LLM port, never on a concrete SDK."""

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.llm.base import LLMClient, LLMMessage
from app.llm.tools import AuthContext, SHIPMENT_TOOLS, execute_tool_call
from app.repositories.shipments import ShipmentRepository

SYSTEM_PROMPT = (
    "You are the SecureShip assistant. You help customers with questions about "
    "their shipments, tracking, and deliveries. Be concise and friendly. "
    "If you don't know something, say so instead of guessing."
)


class ChatService:
    def __init__(self, llm_client: LLMClient, shipment_repository: ShipmentRepository) -> None:
        self._llm_client = llm_client
        self._shipment_repository = shipment_repository

    async def agent_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        auth_context: AuthContext,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the agent loop and yield structured events for SSE transport."""

        conversation = [LLMMessage(role="system", content=SYSTEM_PROMPT), *messages]
        tool_round_happened = False

        for _ in range(20):
            completion = await self._llm_client.plan_chat_turn(conversation, tools=SHIPMENT_TOOLS)

            if completion.tool_calls:
                tool_round_happened = True
                conversation.append(
                    LLMMessage(
                        role="assistant",
                        content=completion.content,
                        tool_calls=completion.tool_calls,
                    )
                )

                for tool_call in completion.tool_calls:
                    try:
                        tool_args = json.loads(tool_call.arguments or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}

                    yield {
                        "type": "tool_call",
                        "tool": tool_call.name,
                        "args": tool_args,
                    }

                    tool_result = execute_tool_call(tool_call, self._shipment_repository, auth_context)
                    yield {
                        "type": "tool_result",
                        "tool": tool_call.name,
                        "result": tool_result,
                    }
                    conversation.append(
                        LLMMessage(
                            role="tool",
                            content=json.dumps(tool_result),
                            tool_call_id=tool_call.id,
                        )
                    )
                continue

            if tool_round_happened:
                async for delta in self._llm_client.stream_chat(conversation):
                    yield {"type": "token", "content": delta}
                yield {"type": "done"}
                return

            async for delta in self._llm_client.stream_chat(conversation):
                yield {"type": "token", "content": delta}
            yield {"type": "done"}
            return

        yield {"type": "error", "message": "Max agent turns reached. Please try again."}
