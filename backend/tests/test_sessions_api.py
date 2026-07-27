from __future__ import annotations

import json
import unittest
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.dependencies import get_chat_service, get_chat_session_repository
from app.llm.base import LLMCompletion, LLMMessage, ToolCall
from app.repositories.shipments import ShipmentRepository
from app.services.chat import ChatService
from main import create_app


@dataclass
class FakeChatSession:
    id: UUID
    state: str
    started_at: datetime
    ended_at: datetime | None
    transcript: dict


class FakeChatSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[UUID, FakeChatSession] = {}
        self._tick = 0

    def list_sessions(self, *, include_deleted: bool = False) -> list[FakeChatSession]:
        sessions = list(self.sessions.values())
        if not include_deleted:
            sessions = [session for session in sessions if session.state != "deleted"]
        sessions.sort(key=lambda item: item.started_at, reverse=True)
        return sessions

    def create_session(self, now: datetime) -> FakeChatSession:
        self._tick += 1
        started_at = now + timedelta(seconds=self._tick)
        session = FakeChatSession(
            id=uuid4(),
            state="active",
            started_at=started_at,
            ended_at=None,
            transcript={"version": 1, "title": None, "events": []},
        )
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID, *, include_deleted: bool = False) -> FakeChatSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if not include_deleted and session.state == "deleted":
            return None
        return session

    def soft_delete_session(self, session_id: UUID, now: datetime) -> FakeChatSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.state = "deleted"
        session.ended_at = now
        return session

    def append_events(self, session_id: UUID, events: list[dict]) -> FakeChatSession | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session.transcript.setdefault("events", []).extend(events)
        if not session.transcript.get("title"):
            for event in session.transcript["events"]:
                if event.get("type") == "message" and event.get("role") == "user":
                    content = " ".join(str(event.get("content") or "").split()).strip()
                    if content:
                        session.transcript["title"] = content[:57] + "..." if len(content) > 60 else content
                        break
        return session


class FakeLLMClient:
    def __init__(self, completions: list[LLMCompletion], stream_chunks: list[str]) -> None:
        self._completions = completions
        self._stream_chunks = stream_chunks

    async def plan_chat_turn(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
    ) -> LLMCompletion:
        return self._completions.pop(0)

    async def stream_chat(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        for chunk in self._stream_chunks:
            yield chunk


class FakeShipmentRepository(ShipmentRepository):
    def __init__(self) -> None:
        pass

    def get_shipment_by_tracking_number(self, tracking_number: str) -> dict | None:
        if tracking_number != "TRK123":
            return None
        return {"tracking_number": "TRK123", "status": "in_transit"}


class SessionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeChatSessionRepository()
        self.app = create_app()
        self.app.dependency_overrides[get_chat_session_repository] = lambda: self.repository
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_create_and_list_sessions_newest_first(self) -> None:
        first = self.client.post("/api/sessions")
        second = self.client.post("/api/sessions")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        listed = self.client.get("/api/sessions")
        self.assertEqual(listed.status_code, 200)
        payload = listed.json()

        self.assertEqual(len(payload["sessions"]), 2)
        self.assertEqual(payload["sessions"][0]["id"], second.json()["session"]["id"])
        self.assertEqual(payload["sessions"][1]["id"], first.json()["session"]["id"])

    def test_soft_delete_excludes_session_from_list(self) -> None:
        created = self.client.post("/api/sessions").json()["session"]

        deleted = self.client.delete(f"/api/sessions/{created['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["session"]["state"], "deleted")

        listed = self.client.get("/api/sessions").json()["sessions"]
        self.assertEqual(listed, [])

    def test_get_session_returns_transcript(self) -> None:
        created = self.client.post("/api/sessions").json()["session"]
        session_id = UUID(created["id"])
        self.repository.append_events(
            session_id,
            [
                {
                    "id": "evt_1",
                    "type": "message",
                    "role": "user",
                    "content": "Track TRK123",
                },
                {
                    "id": "evt_2",
                    "type": "message",
                    "role": "assistant",
                    "content": "Shipment is in transit.",
                },
            ],
        )

        response = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["session"]["id"], str(session_id))
        self.assertEqual(payload["transcript"]["version"], 1)
        self.assertEqual(len(payload["transcript"]["events"]), 2)
        self.assertEqual(payload["transcript"]["events"][0]["role"], "user")

    def test_get_session_404_when_missing(self) -> None:
        response = self.client.get(f"/api/sessions/{uuid4()}")
        self.assertEqual(response.status_code, 404)


class ChatPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeChatSessionRepository()
        self.app = create_app()
        self.app.dependency_overrides[get_chat_session_repository] = lambda: self.repository
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_chat_requires_session_id(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_chat_creates_session_when_session_id_is_null(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "session_id": None,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "session"', response.text)
        self.assertEqual(len(self.repository.sessions), 1)

        created_session = next(iter(self.repository.sessions.values()))
        events = created_session.transcript["events"]
        self.assertEqual(events[0]["type"], "message")
        self.assertEqual(events[0]["role"], "user")
        self.assertEqual(events[0]["content"], "hello")

    def test_chat_persists_user_tool_and_assistant_events(self) -> None:
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
            ],
            stream_chunks=["Your shipment is ", "in transit."],
        )
        chat_service = ChatService(llm_client=llm_client, shipment_repository=FakeShipmentRepository())
        self.app.dependency_overrides[get_chat_service] = lambda: chat_service

        session = self.repository.create_session(now=datetime.now(UTC))

        response = self.client.post(
            "/api/chat",
            json={
                "session_id": str(session.id),
                "messages": [{"role": "user", "content": "Where is TRK123?"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data:", response.text)

        events = self.repository.sessions[session.id].transcript["events"]
        event_types = [event["type"] for event in events]
        self.assertEqual(event_types, ["message", "tool_call", "tool_result", "message"])
        self.assertEqual(events[0]["role"], "user")
        self.assertEqual(events[-1]["role"], "assistant")
        self.assertEqual(events[-1]["content"], "Your shipment is in transit.")
