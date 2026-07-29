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
from app.repositories.session_verification import SessionVerificationRepository
from app.repositories.shipments import ShipmentRepository

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


def get_session_verification_repository() -> SessionVerificationRepository:
    return SessionVerificationRepository()
