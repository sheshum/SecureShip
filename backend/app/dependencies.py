"""Dependency-injection wiring.

Routers depend on ChatService; the concrete LLM adapter is chosen here and
nowhere else, so swapping providers never touches business logic or routes.
"""

from functools import lru_cache
from datetime import timedelta
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings
from app.llm.base import LLMClient
from app.llm.litellm_client import LiteLLMClient
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.repositories.shipments import ShipmentRepository
from app.services.auth_session import AuthSessionStore, InMemoryAuthSessionStore
from app.services.auth_gate import AuthGateService
from app.services.chat import ChatService
from app.services.identity_verification import IdentityVerificationService
from app.services.otp import OtpService
from app.services.sms import ConsoleSmsProvider, SmsProvider, SmsService


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm_client(settings: Annotated[Settings, Depends(get_settings)]) -> LLMClient:
    return LiteLLMClient(
        model=settings.llm_model,
        api_base=settings.llm_api_base,
        api_key=settings.llm_api_key,
    )


def get_shipment_repository() -> ShipmentRepository:
    return ShipmentRepository()


def get_chat_session_repository() -> ChatSessionRepository:
    return ChatSessionRepository()


def get_customer_repository() -> CustomerRepository:
    return CustomerRepository()


@lru_cache
def get_auth_session_store() -> AuthSessionStore:
    settings = get_settings()
    return InMemoryAuthSessionStore(
        auth_ttl=timedelta(seconds=settings.auth_session_ttl_seconds),
        otp_ttl=timedelta(seconds=settings.otp_ttl_seconds),
        otp_resend_cooldown=timedelta(seconds=settings.otp_resend_cooldown_seconds),
    )


@lru_cache
def get_sms_provider() -> SmsProvider:
    settings = get_settings()
    if settings.sms_provider == "console":
        return ConsoleSmsProvider()
    return ConsoleSmsProvider()


def get_sms_service(
    provider: Annotated[SmsProvider, Depends(get_sms_provider)],
) -> SmsService:
    return SmsService(provider)


def get_otp_service(
    auth_session_store: Annotated[AuthSessionStore, Depends(get_auth_session_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OtpService:
    return OtpService(
        auth_session_store,
        max_attempts=settings.otp_max_attempts,
    )


def get_identity_verification_service(
    customer_repository: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> IdentityVerificationService:
    return IdentityVerificationService(customer_repository)


def get_chat_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    shipment_repository: Annotated[ShipmentRepository, Depends(get_shipment_repository)],
) -> ChatService:
    return ChatService(llm_client, shipment_repository)


def get_auth_gate_service(
    identity_service: Annotated[IdentityVerificationService, Depends(get_identity_verification_service)],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    sms_service: Annotated[SmsService, Depends(get_sms_service)],
    session_repository: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> AuthGateService:
    return AuthGateService(identity_service, otp_service, sms_service, session_repository)
