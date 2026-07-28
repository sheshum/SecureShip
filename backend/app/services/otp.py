from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Literal
from uuid import UUID

from app.services.auth_session import AuthSessionStore

OtpErrorCode = Literal[
    "invalid_code",
    "expired_code",
    "too_many_attempts",
    "resend_cooldown",
]


@dataclass(frozen=True)
class OtpIssueResult:
    ok: bool
    otp_code: str | None = None
    error_code: OtpErrorCode | None = None
    retry_at: datetime | None = None


@dataclass(frozen=True)
class OtpVerifyResult:
    ok: bool
    error_code: OtpErrorCode | None = None
    remaining_attempts: int | None = None


class OtpService:
    def __init__(
        self,
        auth_session_store: AuthSessionStore,
        *,
        max_attempts: int,
        code_generator: Callable[[], str] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._auth_session_store = auth_session_store
        self._max_attempts = max_attempts
        self._code_generator = code_generator or _generate_otp_code
        self._now_provider = now_provider or _utc_now

    def issue_code(
        self,
        session_id: UUID,
        *,
        pending_customer_id: UUID | None = None,
        now: datetime | None = None,
    ) -> OtpIssueResult:
        current_time = now or self._now_provider()
        existing = self._auth_session_store.get(session_id)
        if (
            existing is not None
            and existing.otp_resend_available_at is not None
            and existing.otp_resend_available_at > current_time
        ):
            return OtpIssueResult(
                ok=False,
                error_code="resend_cooldown",
                retry_at=existing.otp_resend_available_at,
            )

        otp_code = self._code_generator()
        otp_hash = _hash_otp_code(otp_code)
        otp_expires_at = self._auth_session_store.next_otp_expiry(now=current_time)
        resend_available_at = self._auth_session_store.next_resend_available_at(now=current_time)

        self._auth_session_store.upsert(
            session_id,
            auth_state="awaiting_code",
            now=current_time,
            pending_customer_id=pending_customer_id
            if pending_customer_id is not None
            else (existing.pending_customer_id if existing else None),
            verified_customer_id=existing.verified_customer_id if existing else None,
            otp_code_hash=otp_hash,
            otp_expires_at=otp_expires_at,
            otp_attempt_count=0,
            otp_resend_available_at=resend_available_at,
        )

        return OtpIssueResult(ok=True, otp_code=otp_code)

    def verify_code(
        self,
        session_id: UUID,
        code: str,
        *,
        now: datetime | None = None,
    ) -> OtpVerifyResult:
        current_time = now or self._now_provider()
        existing = self._auth_session_store.get(session_id)
        if existing is None or existing.otp_code_hash is None or existing.otp_expires_at is None:
            return OtpVerifyResult(ok=False, error_code="expired_code", remaining_attempts=0)

        if existing.otp_expires_at <= current_time:
            self._clear_challenge(session_id, existing, now=current_time)
            return OtpVerifyResult(ok=False, error_code="expired_code", remaining_attempts=0)

        if existing.otp_attempt_count >= self._max_attempts:
            self._clear_challenge(session_id, existing, now=current_time)
            return OtpVerifyResult(ok=False, error_code="too_many_attempts", remaining_attempts=0)

        if not _verify_otp_code_hash(code, existing.otp_code_hash):
            updated = self._auth_session_store.record_otp_attempt(session_id, now=current_time)
            remaining_attempts = max(self._max_attempts - updated.otp_attempt_count, 0)
            if updated.otp_attempt_count >= self._max_attempts:
                self._clear_challenge(session_id, updated, now=current_time)
                return OtpVerifyResult(
                    ok=False,
                    error_code="too_many_attempts",
                    remaining_attempts=0,
                )
            return OtpVerifyResult(
                ok=False,
                error_code="invalid_code",
                remaining_attempts=remaining_attempts,
            )

        self._auth_session_store.upsert(
            session_id,
            auth_state="verified" if existing.verified_customer_id is not None else existing.auth_state,
            now=current_time,
            auth_expires_at=existing.auth_expires_at,
            pending_customer_id=existing.pending_customer_id,
            verified_customer_id=existing.verified_customer_id,
            otp_code_hash=None,
            otp_expires_at=None,
            otp_attempt_count=0,
            otp_resend_available_at=None,
        )

        return OtpVerifyResult(ok=True, remaining_attempts=self._max_attempts)

    def _clear_challenge(self, session_id: UUID, session, *, now: datetime) -> None:
        self._auth_session_store.upsert(
            session_id,
            auth_state=session.auth_state,
            now=now,
            auth_expires_at=session.auth_expires_at,
            pending_customer_id=session.pending_customer_id,
            verified_customer_id=session.verified_customer_id,
            otp_code_hash=None,
            otp_expires_at=None,
            otp_attempt_count=0,
            otp_resend_available_at=None,
        )


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp_code(code: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return f"v1${salt}${digest}"


def _verify_otp_code_hash(code: str, otp_hash: str) -> bool:
    try:
        version, salt, expected_digest = otp_hash.split("$", 2)
    except ValueError:
        return False
    if version != "v1":
        return False
    actual_digest = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual_digest, expected_digest)


def _utc_now() -> datetime:
    return datetime.now(UTC)
