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
from app.repositories.shipments import ShipmentRepository
from app.services.auth_session import AuthSessionStore, InMemoryAuthSessionStore
from app.services.chat import ChatService


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


@lru_cache
def get_auth_session_store() -> AuthSessionStore:
    settings = get_settings()
    return InMemoryAuthSessionStore(
        auth_ttl=timedelta(seconds=settings.auth_session_ttl_seconds),
        otp_ttl=timedelta(seconds=settings.otp_ttl_seconds),
        otp_resend_cooldown=timedelta(seconds=settings.otp_resend_cooldown_seconds),
    )


def get_chat_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    shipment_repository: Annotated[ShipmentRepository, Depends(get_shipment_repository)],
) -> ChatService:
    return ChatService(llm_client, shipment_repository)
