"""Dependency-injection wiring.

Routers depend on ChatService; the concrete LLM adapter is chosen here and
nowhere else, so swapping providers never touches business logic or routes.
"""

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends

from app.agent import SYSTEM_PROMPT, Agent
from app.core.config import Settings
from app.llm.base import LLMClient
from app.llm.litellm_client import LiteLLMClient
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.repositories.session_verification import SessionVerificationRepository
from app.repositories.shipments import ShipmentRepository
from app.tools.escalate_to_human import EscalateToHumanTool

# Tool dependencies - tools are constructed per-request with their dependencies
from app.tools.lookup_shipments import LookupShipmentsTool
from app.tools.request_identity_info import RequestIdentityInfoTool
from app.tools.tool_registry import TOOL_REGISTRY, get_tool_metadata, register_tool
from app.tools.verify_identity import VerifyIdentityTool


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



def get_verify_identity_tool(
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    verification_repo: Annotated[
        SessionVerificationRepository, Depends(get_session_verification_repository)
    ],
) -> VerifyIdentityTool:
    """Dependency that constructs VerifyIdentityTool with its dependencies."""
    return VerifyIdentityTool(
        customer_repo=customer_repo,
        session_repo=session_repo,
        verification_repo=verification_repo,
    )


def get_lookup_shipments_tool(
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)],
) -> LookupShipmentsTool:
    """Dependency that constructs LookupShipmentsTool with its dependencies."""
    return LookupShipmentsTool(shipment_repo=shipment_repo)


def get_request_identity_info_tool() -> RequestIdentityInfoTool:
    """Dependency that constructs RequestIdentityInfoTool (no dependencies needed)."""
    return RequestIdentityInfoTool()

def get_escalate_to_human_tool() -> EscalateToHumanTool:
    """Dependency that constructs EscalateToHumanTool (no dependencies needed)."""
    return EscalateToHumanTool()


def get_tool_registry(
    verify_identity_tool: Annotated[VerifyIdentityTool, Depends(get_verify_identity_tool)],
    lookup_shipments_tool: Annotated[LookupShipmentsTool, Depends(get_lookup_shipments_tool)],
    request_identity_info_tool: Annotated[
        RequestIdentityInfoTool, Depends(get_request_identity_info_tool)
    ],
    escalate_to_human_tool: Annotated[
        EscalateToHumanTool, Depends(get_escalate_to_human_tool)
    ],
) -> dict[str, Any]:
    """Dependency that builds and returns the tool registry with all tools.

    This is called per-request, ensuring tools are freshly constructed with
    their dependencies via FastAPI DI. Returns the TOOL_REGISTRY dict after
    populating it with the current tool instances.
    """
    # Clear the registry (in case of hot reload)
    TOOL_REGISTRY.clear()

    # Register each tool with its metadata from the @tool decorator
    for tool_instance in [
        verify_identity_tool,
        lookup_shipments_tool,
        request_identity_info_tool,
        escalate_to_human_tool,
    ]:
        tool_class = type(tool_instance)
        name, schema, requires_verification = get_tool_metadata(tool_class)
        register_tool(
            name=name,
            schema=schema,
            handler=tool_instance,
            requires_verification=requires_verification,
        )

    return TOOL_REGISTRY


def get_agent(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    tool_registry: Annotated[dict, Depends(get_tool_registry)],
) -> Agent:
    """Construct Agent with injected dependencies."""
    return Agent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        system_prompt=SYSTEM_PROMPT,
    )
