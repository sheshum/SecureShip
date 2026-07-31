"""Repository for SessionVerification entity.

Handles all database operations for OTP verification lifecycle.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import SessionVerification


class SessionVerificationRepository:
    """Repository for managing OTP verification lifecycle."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def create(
        self,
        *,
        session_id: UUID,
        code_hash: str,
        matched_customer_id: UUID,
        sent_at: datetime,
        expires_at: datetime,
    ) -> SessionVerification:
        """Create a new OTP verification record for a session.

        Args:
            session_id: The chat session being verified
            code_hash: SHA-256 hash of the 6-digit OTP code
            matched_customer_id: Customer that passed identity verification
            sent_at: When the OTP was generated
            expires_at: When the OTP expires (typically sent_at + 7 minutes)

        Returns:
            The created SessionVerification record
        """
        with self._session_factory() as session:
            verification = SessionVerification(
                session_id=session_id,
                code_hash=code_hash,
                matched_customer_id=matched_customer_id,
                sent_at=sent_at,
                expires_at=expires_at,
                attempts=0,
                status="pending",
            )
            session.add(verification)
            session.commit()
            session.refresh(verification)
            return verification

    def get_by_session(self, session_id: UUID) -> SessionVerification | None:
        """Retrieve verification record by session ID.

        Args:
            session_id: The chat session ID

        Returns:
            SessionVerification record if found, None otherwise
        """
        with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(SessionVerification).where(SessionVerification.session_id == session_id)
            return session.scalar(stmt)

    def increment_attempt(self, session_id: UUID) -> SessionVerification | None:
        """Increment the failed attempt counter for a session.

        Args:
            session_id: The chat session ID

        Returns:
            Updated SessionVerification record if found, None otherwise
        """
        with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(SessionVerification).where(SessionVerification.session_id == session_id)
            verification = session.scalar(stmt)
            if verification is None:
                return None

            verification.attempts += 1
            session.commit()
            session.refresh(verification)
            return verification

    def update_status(self, session_id: UUID, status: str) -> SessionVerification | None:
        """Update the status of a verification record.

        Args:
            session_id: The chat session ID
            status: New status (pending/verified/expired/exhausted)

        Returns:
            Updated SessionVerification record if found, None otherwise
        """
        with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(SessionVerification).where(SessionVerification.session_id == session_id)
            verification = session.scalar(stmt)
            if verification is None:
                return None

            verification.status = status
            session.commit()
            session.refresh(verification)
            return verification

    def delete(self, session_id: UUID) -> None:
        """Delete verification record for a session.

        Args:
            session_id: The chat session ID
        """
        with self._session_factory() as session:
            from sqlalchemy import delete

            stmt = delete(SessionVerification).where(SessionVerification.session_id == session_id)
            session.execute(stmt)
            session.commit()
