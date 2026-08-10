"""Dependency-injection wiring.

Routers depend on ChatService; the concrete LLM adapter is chosen here and
nowhere else, so swapping providers never touches business logic or routes.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi_plugin import Auth0FastAPI

from app.agent import SYSTEM_PROMPT, Agent
from app.core.config import Settings
from app.llm.base import LLMClient
from app.llm.litellm_client import LiteLLMClient
from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.repositories.packages import PackageRepository
from app.repositories.session_verification import SessionVerificationRepository
from app.repositories.shipments import ShipmentRepository
from app.tools.escalate_to_human import EscalateToHumanTool

# Tool dependencies - tools are constructed per-request with their dependencies
from app.tools.lookup_shipments import LookupShipmentsTool
from app.tools.request_identity_info import RequestIdentityInfoTool
from app.tools.tool_registry import ToolSpec, get_tool_metadata
from app.tools.start_identity_verification import StartIdentityVerificationTool


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


def get_package_repository() -> PackageRepository:
    return PackageRepository()


def get_chat_session_repository() -> ChatSessionRepository:
    return ChatSessionRepository()


def get_customer_repository() -> CustomerRepository:
    return CustomerRepository()


def get_session_verification_repository() -> SessionVerificationRepository:
    return SessionVerificationRepository()


def get_start_identity_verification_tool(
    customer_repo: Annotated[CustomerRepository, Depends(get_customer_repository)],
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
    verification_repo: Annotated[SessionVerificationRepository, Depends(get_session_verification_repository)],
) -> StartIdentityVerificationTool:
    """Dependency that constructs StartIdentityVerificationTool with its dependencies."""
    return StartIdentityVerificationTool(
        customer_repo=customer_repo,
        session_repo=session_repo,
        verification_repo=verification_repo,
    )


def get_lookup_shipments_tool(
    shipment_repo: Annotated[ShipmentRepository, Depends(get_shipment_repository)],
) -> LookupShipmentsTool:
    """Dependency that constructs LookupShipmentsTool with its dependencies."""
    return LookupShipmentsTool(shipment_repo=shipment_repo)


def get_request_identity_info_tool(
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> RequestIdentityInfoTool:
    """Dependency that constructs RequestIdentityInfoTool with its dependencies."""
    return RequestIdentityInfoTool(session_repo=session_repo)


def get_escalate_to_human_tool(
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> EscalateToHumanTool:
    """Dependency that constructs EscalateToHumanTool with its dependencies."""
    return EscalateToHumanTool(session_repo=session_repo)


def get_tool_registry(
    verify_identity_tool: Annotated[StartIdentityVerificationTool, Depends(get_start_identity_verification_tool)],
    lookup_shipments_tool: Annotated[LookupShipmentsTool, Depends(get_lookup_shipments_tool)],
    request_identity_info_tool: Annotated[RequestIdentityInfoTool, Depends(get_request_identity_info_tool)],
    escalate_to_human_tool: Annotated[EscalateToHumanTool, Depends(get_escalate_to_human_tool)],
) -> dict[str, ToolSpec]:
    """Build a fresh tool registry for this request.

    Tools are constructed per-request via FastAPI DI (so each gets its own
    repository instances). We return a plain local dict — no shared/global
    state — which is what the dispatcher looks tools up in.
    """
    registry: dict[str, ToolSpec] = {}
    for tool_instance in [
        verify_identity_tool,
        lookup_shipments_tool,
        request_identity_info_tool,
        escalate_to_human_tool,
    ]:
        name, schema, requires_verification = get_tool_metadata(type(tool_instance))
        registry[name] = ToolSpec(
            name=name,
            schema=schema,
            handler=tool_instance,
            requires_verification=requires_verification,
        )
    return registry


def get_agent(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    tool_registry: Annotated[dict[str, ToolSpec], Depends(get_tool_registry)],
) -> Agent:
    """Construct Agent with injected dependencies."""
    return Agent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        system_prompt=SYSTEM_PROMPT,
    )


@lru_cache
def get_auth0_client() -> Auth0FastAPI:
    settings = get_settings()
    return Auth0FastAPI(domain=settings.auth0_domain, audience=settings.auth0_audience)


async def require_admin_auth(request: Request) -> dict:
    """Route dependency gating admin-only endpoints behind a valid Auth0 access token.

    Built lazily (via get_auth0_client) so the app still boots and the public
    chat/auth flow keeps working when AUTH0_DOMAIN/AUTH0_AUDIENCE are unset.
    """
    claims = await get_auth0_client().require_auth()(request)
    if "admin:all" not in claims.get("permissions", []):
        raise HTTPException(status_code=403, detail="Forbidden")
    return claims
