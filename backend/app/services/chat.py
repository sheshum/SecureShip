"""Chat business logic. Depends only on the LLM port, never on a concrete SDK."""

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.llm.base import LLMClient, LLMMessage
from app.llm.tools import (
    AUTH_GATE_TOOLS,
    AuthContext,
    SHIPMENT_TOOLS,
    execute_tool_call,
)
from app.repositories.shipments import ShipmentRepository

SYSTEM_PROMPT = (
    "You are the SecureShip assistant. You help customers with questions about "
    "their shipments, tracking, and deliveries. Respond in a professional but friendly tone. Be concise and clear."
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
        pass

