from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID

from app.schemas.sessions import ChatSessionState

AuthSessionStatus = Literal["valid", "expired", "missing"]


@dataclass(frozen=True)
class AuthSessionRecord:
    session_id: UUID
    auth_state: ChatSessionState
    auth_expires_at: datetime | None = None
    pending_customer_id: UUID | None = None
    verified_customer_id: UUID | None = None
    otp_code_hash: str | None = None
    otp_expires_at: datetime | None = None
    otp_attempt_count: int = 0
    otp_resend_available_at: datetime | None = None


@dataclass(frozen=True)
class AuthSessionLookup:
    status: AuthSessionStatus
    session: AuthSessionRecord | None


class AuthSessionStore(Protocol):
    def get(self, session_id: UUID) -> AuthSessionRecord | None: ...

    def upsert(
        self,
        session_id: UUID,
        *,
        auth_state: ChatSessionState,
        now: datetime | None = None,
        auth_expires_at: datetime | None = None,
        pending_customer_id: UUID | None = None,
        verified_customer_id: UUID | None = None,
        otp_code_hash: str | None = None,
        otp_expires_at: datetime | None = None,
        otp_attempt_count: int = 0,
        otp_resend_available_at: datetime | None = None,
    ) -> AuthSessionRecord: ...

    def mark_auth_required(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord: ...

    def mark_verified(
        self,
        session_id: UUID,
        verified_customer_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AuthSessionRecord: ...

    def record_otp_attempt(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord: ...

    def reset_identity_flow(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord: ...

    def expire_if_needed(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionLookup: ...

    def delete(self, session_id: UUID) -> None: ...


class InMemoryAuthSessionStore:
    def __init__(
        self,
        *,
        auth_ttl: timedelta,
        otp_ttl: timedelta,
        otp_resend_cooldown: timedelta,
    ) -> None:
        self._auth_ttl = auth_ttl
        self._otp_ttl = otp_ttl
        self._otp_resend_cooldown = otp_resend_cooldown
        self._sessions: dict[UUID, AuthSessionRecord] = {}

    def get(self, session_id: UUID) -> AuthSessionRecord | None:
        record = self._sessions.get(session_id)
        if record is None:
            return None
        return replace(record)

    def upsert(
        self,
        session_id: UUID,
        *,
        auth_state: ChatSessionState,
        now: datetime | None = None,
        auth_expires_at: datetime | None = None,
        pending_customer_id: UUID | None = None,
        verified_customer_id: UUID | None = None,
        otp_code_hash: str | None = None,
        otp_expires_at: datetime | None = None,
        otp_attempt_count: int = 0,
        otp_resend_available_at: datetime | None = None,
    ) -> AuthSessionRecord:
        current_time = now or _utc_now()
        record = AuthSessionRecord(
            session_id=session_id,
            auth_state=auth_state,
            auth_expires_at=auth_expires_at,
            pending_customer_id=pending_customer_id,
            verified_customer_id=verified_customer_id,
            otp_code_hash=otp_code_hash,
            otp_expires_at=otp_expires_at,
            otp_attempt_count=otp_attempt_count,
            otp_resend_available_at=otp_resend_available_at,
        )
        if record.auth_expires_at is None and record.auth_state == "verified":
            record = replace(record, auth_expires_at=current_time + self._auth_ttl)
        self._sessions[session_id] = record
        return replace(record)

    def mark_auth_required(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord:
        existing = self._sessions.get(session_id)
        record = AuthSessionRecord(
            session_id=session_id,
            auth_state="collecting_identity",
            auth_expires_at=None,
            pending_customer_id=existing.pending_customer_id if existing else None,
            verified_customer_id=None,
            otp_code_hash=None,
            otp_expires_at=None,
            otp_attempt_count=0,
            otp_resend_available_at=None,
        )
        self._sessions[session_id] = record
        return replace(record)

    def mark_verified(
        self,
        session_id: UUID,
        verified_customer_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AuthSessionRecord:
        current_time = now or _utc_now()
        record = AuthSessionRecord(
            session_id=session_id,
            auth_state="verified",
            auth_expires_at=current_time + self._auth_ttl,
            pending_customer_id=None,
            verified_customer_id=verified_customer_id,
            otp_code_hash=None,
            otp_expires_at=None,
            otp_attempt_count=0,
            otp_resend_available_at=None,
        )
        self._sessions[session_id] = record
        return replace(record)

    def record_otp_attempt(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord:
        existing = self._sessions.get(session_id)
        if existing is None:
            existing = AuthSessionRecord(session_id=session_id, auth_state="awaiting_code")

        record = replace(existing, otp_attempt_count=existing.otp_attempt_count + 1)
        self._sessions[session_id] = record
        return replace(record)

    def reset_identity_flow(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionRecord:
        record = AuthSessionRecord(
            session_id=session_id,
            auth_state="collecting_identity",
            auth_expires_at=None,
            pending_customer_id=None,
            verified_customer_id=None,
            otp_code_hash=None,
            otp_expires_at=None,
            otp_attempt_count=0,
            otp_resend_available_at=None,
        )
        self._sessions[session_id] = record
        return replace(record)

    def expire_if_needed(self, session_id: UUID, *, now: datetime | None = None) -> AuthSessionLookup:
        current_time = now or _utc_now()
        record = self._sessions.get(session_id)
        if record is None:
            return AuthSessionLookup(status="missing", session=None)

        if record.auth_expires_at is not None and record.auth_expires_at <= current_time:
            expired_snapshot = replace(record)
            del self._sessions[session_id]
            return AuthSessionLookup(status="expired", session=expired_snapshot)

        return AuthSessionLookup(status="valid", session=replace(record))

    def delete(self, session_id: UUID) -> None:
        self._sessions.pop(session_id, None)

    def next_otp_expiry(self, *, now: datetime | None = None) -> datetime:
        current_time = now or _utc_now()
        return current_time + self._otp_ttl

    def next_resend_available_at(self, *, now: datetime | None = None) -> datetime:
        current_time = now or _utc_now()
        return current_time + self._otp_resend_cooldown


def _utc_now() -> datetime:
    return datetime.now(UTC)