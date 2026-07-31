import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SHIPMENT_STATUSES = (
    "label_created",
    "in_transit",
    "out_for_delivery",
    "delivered",
    "exception",
)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(255))

    shipments: Mapped[list["Shipment"]] = relationship(back_populates="customer")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="customer")


class Shipment(Base):
    __tablename__ = "shipment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer.id"), index=True
    )
    tracking_number: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(Enum(*SHIPMENT_STATUSES, name="shipment_status"))
    carrier: Mapped[str] = mapped_column(String(100))
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    estimated_delivery: Mapped[date] = mapped_column(Date)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="shipments")
    packages: Mapped[list["Package"]] = relationship(back_populates="shipment")


class Package(Base):
    __tablename__ = "package"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipment.id"), index=True
    )
    description: Mapped[str] = mapped_column(String(255))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    declared_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    shipment: Mapped[Shipment] = relationship(back_populates="packages")


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable until the chat user completes identity verification.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer.id"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    customer: Mapped[Customer | None] = relationship(back_populates="chat_sessions")
    session_verification: Mapped["SessionVerification | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class SessionVerification(Base):
    """OTP verification data for a chat session.

    One-to-one relationship with ChatSession. Stores only OTP lifecycle data:
    - code_hash: SHA-256 hash of the 6-digit code (never plain text)
    - attempts: Number of failed verification attempts (max 3)
    - sent_at, expires_at: OTP validity window
    - status: Current state (pending/verified/expired/exhausted)
    - matched_customer_id: Customer that passed identity verification
    """

    __tablename__ = "session_verification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    matched_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer.id")
    )

    session: Mapped[ChatSession] = relationship(back_populates="session_verification")
    matched_customer: Mapped[Customer] = relationship()


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    idp_subject: Mapped[str] = mapped_column(Text)
