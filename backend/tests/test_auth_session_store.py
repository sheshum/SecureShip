from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.auth_session import InMemoryAuthSessionStore


class AuthSessionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryAuthSessionStore(
            auth_ttl=timedelta(minutes=30),
            otp_ttl=timedelta(minutes=5),
            otp_resend_cooldown=timedelta(seconds=45),
        )
        self.now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)

    def test_expire_if_needed_returns_missing_when_no_record(self) -> None:
        lookup = self.store.expire_if_needed(uuid4(), now=self.now)

        self.assertEqual(lookup.status, "missing")
        self.assertIsNone(lookup.session)

    def test_mark_verified_creates_valid_record_with_expiry(self) -> None:
        session_id = uuid4()
        customer_id = uuid4()

        record = self.store.mark_verified(session_id, customer_id, now=self.now)

        self.assertEqual(record.auth_state, "verified")
        self.assertEqual(record.verified_customer_id, customer_id)
        self.assertEqual(record.auth_expires_at, self.now + timedelta(minutes=30))

        lookup = self.store.expire_if_needed(session_id, now=self.now + timedelta(minutes=10))
        self.assertEqual(lookup.status, "valid")
        self.assertIsNotNone(lookup.session)
        self.assertEqual(lookup.session.verified_customer_id, customer_id)

    def test_expire_if_needed_deletes_expired_record(self) -> None:
        session_id = uuid4()
        customer_id = uuid4()
        self.store.mark_verified(session_id, customer_id, now=self.now)

        expired_lookup = self.store.expire_if_needed(session_id, now=self.now + timedelta(minutes=31))
        self.assertEqual(expired_lookup.status, "expired")
        self.assertIsNotNone(expired_lookup.session)
        self.assertEqual(expired_lookup.session.verified_customer_id, customer_id)

        missing_lookup = self.store.expire_if_needed(session_id, now=self.now + timedelta(minutes=31))
        self.assertEqual(missing_lookup.status, "missing")

    def test_record_otp_attempt_increments_counter(self) -> None:
        session_id = uuid4()
        self.store.upsert(session_id, auth_state="awaiting_code", otp_attempt_count=0, now=self.now)

        first = self.store.record_otp_attempt(session_id, now=self.now)
        second = self.store.record_otp_attempt(session_id, now=self.now)

        self.assertEqual(first.otp_attempt_count, 1)
        self.assertEqual(second.otp_attempt_count, 2)

    def test_reset_identity_flow_clears_sensitive_fields(self) -> None:
        session_id = uuid4()
        self.store.upsert(
            session_id,
            auth_state="awaiting_code",
            now=self.now,
            pending_customer_id=uuid4(),
            verified_customer_id=uuid4(),
            otp_code_hash="hashed",
            otp_expires_at=self.now + timedelta(minutes=5),
            otp_attempt_count=3,
            otp_resend_available_at=self.now + timedelta(seconds=45),
        )

        record = self.store.reset_identity_flow(session_id, now=self.now)

        self.assertEqual(record.auth_state, "collecting_identity")
        self.assertIsNone(record.pending_customer_id)
        self.assertIsNone(record.verified_customer_id)
        self.assertIsNone(record.otp_code_hash)
        self.assertIsNone(record.otp_expires_at)
        self.assertEqual(record.otp_attempt_count, 0)
        self.assertIsNone(record.otp_resend_available_at)

    def test_helpers_return_config_driven_timestamps(self) -> None:
        self.assertEqual(self.store.next_otp_expiry(now=self.now), self.now + timedelta(minutes=5))
        self.assertEqual(
            self.store.next_resend_available_at(now=self.now),
            self.now + timedelta(seconds=45),
        )
