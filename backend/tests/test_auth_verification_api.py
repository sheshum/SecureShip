from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.dependencies import (
    get_auth_session_store,
    get_chat_session_repository,
    get_otp_service,
)
from app.services.auth_session import InMemoryAuthSessionStore
from app.services.otp import OtpService
from main import create_app


@dataclass
class FakeChatSession:
    id: UUID
    state: str
    started_at: datetime
    ended_at: datetime | None
    customer_id: UUID | None
    transcript: dict


class FakeChatSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[UUID, FakeChatSession] = {}

    def get_session(self, session_id: UUID) -> FakeChatSession | None:
        return self.sessions.get(session_id)

    def create_session(self, now: datetime) -> FakeChatSession:
        session = FakeChatSession(
            id=uuid4(),
            state="anonymous",
            started_at=now,
            ended_at=None,
            customer_id=None,
            transcript={"version": 1, "title": None, "events": []},
        )
        self.sessions[session.id] = session
        return session

    def update_auth_state(
        self,
        session_id: UUID,
        *,
        state: str,
        customer_id: UUID | None,
    ) -> FakeChatSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.state = state
        session.customer_id = customer_id
        return session

    def get_pending_turn(self, session_id: UUID) -> dict | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        return session.transcript.get("pending_turn")


class VerifyCodeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
        self.repository = FakeChatSessionRepository()
        self.session = self.repository.create_session(now=self.now)
        self.identity_customer_id = uuid4()

        self.auth_store = InMemoryAuthSessionStore(
            auth_ttl=timedelta(minutes=30),
            otp_ttl=timedelta(minutes=5),
            otp_resend_cooldown=timedelta(seconds=45),
        )
        self.otp_service = OtpService(
            self.auth_store,
            max_attempts=3,
            code_generator=lambda: "123456",
            now_provider=lambda: self.now,
        )

        self.app = create_app()
        self.app.dependency_overrides[get_chat_session_repository] = lambda: self.repository
        self.app.dependency_overrides[get_auth_session_store] = lambda: self.auth_store
        self.app.dependency_overrides[get_otp_service] = lambda: self.otp_service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _issue_otp(self) -> None:
        self.otp_service.issue_code(
            self.session.id,
            pending_customer_id=self.identity_customer_id,
        )

    def test_verify_code_success_binds_customer_and_marks_verified(self) -> None:
        self._issue_otp()

        response = self.client.post(
            "/api/verify-code",
            json={"session_id": str(self.session.id), "code": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["state"], "verified")

        session = self.repository.sessions[self.session.id]
        self.assertEqual(session.state, "verified")
        self.assertEqual(session.customer_id, self.identity_customer_id)

    def test_verify_code_invalid_returns_remaining_attempts(self) -> None:
        self._issue_otp()

        response = self.client.post(
            "/api/verify-code",
            json={"session_id": str(self.session.id), "code": "000000"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["state"], "awaiting_code")
        self.assertEqual(payload["error_code"], "invalid_code")
        self.assertEqual(payload["remaining_attempts"], 2)

    def test_verify_code_expired_resets_to_collecting_identity(self) -> None:
        self._issue_otp()

        # Move challenge expiry into the past to force expired_code branch.
        record = self.auth_store.get(self.session.id)
        self.auth_store.upsert(
            self.session.id,
            auth_state=record.auth_state,
            now=self.now,
            pending_customer_id=record.pending_customer_id,
            verified_customer_id=record.verified_customer_id,
            otp_code_hash=record.otp_code_hash,
            otp_expires_at=self.now - timedelta(seconds=1),
            otp_attempt_count=record.otp_attempt_count,
            otp_resend_available_at=record.otp_resend_available_at,
            auth_expires_at=record.auth_expires_at,
        )

        response = self.client.post(
            "/api/verify-code",
            json={"session_id": str(self.session.id), "code": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["error_code"], "expired_code")
        self.assertEqual(payload["state"], "collecting_identity")
        self.assertEqual(self.repository.sessions[self.session.id].state, "collecting_identity")

