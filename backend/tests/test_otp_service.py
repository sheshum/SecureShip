from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.auth_session import InMemoryAuthSessionStore
from app.services.otp import OtpService


class OtpServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
        self.store = InMemoryAuthSessionStore(
            auth_ttl=timedelta(minutes=30),
            otp_ttl=timedelta(minutes=5),
            otp_resend_cooldown=timedelta(seconds=45),
        )
        self.service = OtpService(
            self.store,
            max_attempts=3,
            code_generator=lambda: "123456",
            now_provider=lambda: self.now,
        )

    def test_issue_code_sets_hashed_challenge_and_returns_plain_code(self) -> None:
        session_id = uuid4()

        result = self.service.issue_code(session_id, now=self.now)

        self.assertTrue(result.ok)
        self.assertEqual(result.otp_code, "123456")

        record = self.store.get(session_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.auth_state, "awaiting_code")
        self.assertIsNotNone(record.otp_code_hash)
        self.assertNotIn("123456", record.otp_code_hash)
        self.assertEqual(record.otp_attempt_count, 0)

    def test_issue_code_enforces_resend_cooldown(self) -> None:
        session_id = uuid4()
        self.service.issue_code(session_id, now=self.now)

        result = self.service.issue_code(session_id, now=self.now + timedelta(seconds=10))

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "resend_cooldown")
        self.assertEqual(result.retry_at, self.now + timedelta(seconds=45))

    def test_verify_code_returns_invalid_code_with_remaining_attempts(self) -> None:
        session_id = uuid4()
        self.service.issue_code(session_id, now=self.now)

        result = self.service.verify_code(session_id, "000000", now=self.now + timedelta(seconds=1))

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_code")
        self.assertEqual(result.remaining_attempts, 2)

    def test_verify_code_returns_too_many_attempts(self) -> None:
        session_id = uuid4()
        self.service.issue_code(session_id, now=self.now)

        self.service.verify_code(session_id, "000000", now=self.now + timedelta(seconds=1))
        self.service.verify_code(session_id, "000000", now=self.now + timedelta(seconds=2))
        result = self.service.verify_code(session_id, "000000", now=self.now + timedelta(seconds=3))

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "too_many_attempts")
        self.assertEqual(result.remaining_attempts, 0)

    def test_verify_code_returns_expired_code(self) -> None:
        session_id = uuid4()
        self.service.issue_code(session_id, now=self.now)

        result = self.service.verify_code(session_id, "123456", now=self.now + timedelta(minutes=6))

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "expired_code")
        self.assertEqual(result.remaining_attempts, 0)

    def test_verify_code_success_clears_challenge(self) -> None:
        session_id = uuid4()
        self.service.issue_code(session_id, now=self.now)

        result = self.service.verify_code(session_id, "123456", now=self.now + timedelta(seconds=1))

        self.assertTrue(result.ok)
        record = self.store.get(session_id)
        self.assertIsNotNone(record)
        self.assertIsNone(record.otp_code_hash)
        self.assertIsNone(record.otp_expires_at)
        self.assertEqual(record.otp_attempt_count, 0)
