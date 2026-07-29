from __future__ import annotations

import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from uuid import uuid4

from app.llm.base import LLMCompletion, LLMMessage, ToolCall
from app.llm.tools import AuthContext, execute_tool_call
from app.repositories.shipments import ShipmentRepository
from app.services.chat import ChatService


class FakeLLMClient:
    def __init__(self, completions: list[LLMCompletion], stream_chunks: list[str] | None = None) -> None:
        self._completions = completions
        self._stream_chunks = stream_chunks or []
        self.complete_calls: list[tuple[list[LLMMessage], list[dict] | None]] = []
        self.stream_calls: list[list[LLMMessage]] = []

    async def plan_chat_turn(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
    ) -> LLMCompletion:
        self.complete_calls.append((list(messages), tools))
        return self._completions.pop(0)

    async def stream_chat(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        self.stream_calls.append(list(messages))
        for chunk in self._stream_chunks:
            yield chunk


class FakeShipmentRepository(ShipmentRepository):
    def __init__(self) -> None:
        self.tracking_numbers: list[str] = []
        self.customer_ids: list[str] = []

    def get_shipment_by_tracking_number_for_customer(self, tracking_number: str, customer_id) -> dict | None:
        self.tracking_numbers.append(tracking_number)
        self.customer_ids.append(str(customer_id))
        if tracking_number == "TRK123":
            return {
                "tracking_number": tracking_number,
                "status": "in_transit",
            }
        return None

    def get_shipments_for_customer(self, customer_id) -> dict:
        customer_id_str = str(customer_id)
        self.customer_ids.append(customer_id_str)
        return {
            "found": True,
            "customer": {"id": customer_id_str},
            "shipments": [{"tracking_number": "TRK123"}],
        }


class ToolExecutionTests(unittest.TestCase):
    def test_execute_get_shipment_status(self) -> None:
        repository = FakeShipmentRepository()
        tool_call = ToolCall(
            id="tool-1",
            name="get_shipment_status",
            arguments=json.dumps({"tracking_number": "TRK123"}),
        )

        result = execute_tool_call(
            tool_call,
            repository,
            AuthContext(customer_id=uuid4()),
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["found"])
        self.assertEqual(repository.tracking_numbers, ["TRK123"])

    def test_execute_tool_returns_auth_required_when_unverified(self) -> None:
        repository = FakeShipmentRepository()
        tool_call = ToolCall(
            id="tool-2",
            name="lookup_shipments",
            arguments=json.dumps({}),
        )

        result = execute_tool_call(tool_call, repository, AuthContext(customer_id=None))

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "auth_required")
        self.assertEqual(repository.customer_ids, [])


class ChatServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_stream_uses_tool_then_streams_final_answer(self) -> None:
        llm_client = FakeLLMClient(
            completions=[
                LLMCompletion(
                    content="",
                    tool_calls=(
                        ToolCall(
                            id="tool-1",
                            name="get_shipment_status",
                            arguments=json.dumps({"tracking_number": "TRK123"}),
                        ),
                    ),
                ),
                LLMCompletion(content="Your shipment is in transit."),
            ]
            ,
            stream_chunks=["Your shipment is ", "in transit."],
        )
        repository = FakeShipmentRepository()
        service = ChatService(llm_client, repository)

        output = [
            event
            async for event in service.agent_stream(
                [LLMMessage(role="user", content="Where is TRK123?")],
                auth_context=AuthContext(customer_id=uuid4()),
            )
        ]

        self.assertEqual(
            output,
            [
                {"type": "tool_call", "tool": "get_shipment_status", "args": {"tracking_number": "TRK123"}},
                {"type": "tool_result", "tool": "get_shipment_status", "result": {"ok": True, "found": True, "shipment": {"tracking_number": "TRK123", "status": "in_transit"}}},
                {"type": "token", "content": "Your shipment is "},
                {"type": "token", "content": "in transit."},
                {"type": "done"},
            ],
        )
        self.assertEqual(repository.tracking_numbers, ["TRK123"])
        self.assertEqual(len(llm_client.complete_calls), 2)

    async def test_agent_stream_streams_direct_answer_without_tools(self) -> None:
        llm_client = FakeLLMClient(
            completions=[LLMCompletion(content="Direct answer")],
            stream_chunks=["Direct", " answer"],
        )
        repository = FakeShipmentRepository()
        service = ChatService(llm_client, repository)

        output = [
            event
            async for event in service.agent_stream(
                [LLMMessage(role="user", content="Hello")],
                auth_context=AuthContext(customer_id=uuid4()),
            )
        ]

        self.assertEqual(output, [{"type": "token", "content": "Direct"}, {"type": "token", "content": " answer"}, {"type": "done"}])
        self.assertEqual(len(llm_client.complete_calls), 1)
        self.assertEqual(len(llm_client.stream_calls), 1)
