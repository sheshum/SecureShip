"""LLM tool definitions and execution helpers.

Each tool's schema (and, where applicable, execution logic) lives in its own
module in this package. This file aggregates tools into registry-backed
collections and exposes the shared dispatch entry point.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.llm.base import ToolCall
from app.repositories.shipments import ShipmentRepository

from . import get_shipment_status, lookup_shipments, request_identity_info, verify_identity
from .registry import ToolRegistry, ToolRegistration


@dataclass(frozen=True, slots=True)
class AuthContext:
    customer_id: UUID | None

    @property
    def is_verified(self) -> bool:
        return self.customer_id is not None


TOOL_REGISTRY = ToolRegistry()

TOOL_REGISTRY.register(
    ToolRegistration(
        name="get_shipment_status",
        schema=get_shipment_status.TOOL_SCHEMA,
        execute=get_shipment_status.execute,
        requires_verified_auth=True,
        group="shipment",
    )
)
TOOL_REGISTRY.register(
    ToolRegistration(
        name="lookup_shipments",
        schema=lookup_shipments.TOOL_SCHEMA,
        execute=lookup_shipments.execute,
        requires_verified_auth=True,
        group="shipment",
    )
)
TOOL_REGISTRY.register(
    ToolRegistration(
        name="request_identity_info",
        schema=request_identity_info.TOOL_SCHEMA,
        execute=request_identity_info.execute,
        requires_verified_auth=False,
        group="auth_gate",
    )
)
TOOL_REGISTRY.register(
    ToolRegistration(
        name="verify_identity",
        schema=verify_identity.TOOL_SCHEMA,
        execute=verify_identity.execute,
        requires_verified_auth=False,
        group="auth_gate",
    )
)

SHIPMENT_TOOLS: list[dict[str, Any]] = TOOL_REGISTRY.schemas_for_group("shipment")
AUTH_GATE_TOOLS: list[dict[str, Any]] = TOOL_REGISTRY.schemas_for_group("auth_gate")


def execute_tool_call(
    tool_call: ToolCall,
    shipment_repository: ShipmentRepository,
    auth_context: AuthContext,
) -> dict[str, Any]:
    try:
        arguments = json.loads(tool_call.arguments or "{}")
    except json.JSONDecodeError:
        arguments = {}

    tool = TOOL_REGISTRY.get(tool_call.name)
    if tool is None:
        return {
            "ok": False,
            "error": f"Unknown tool: {tool_call.name}",
        }

    if tool.requires_verified_auth and (not auth_context.is_verified or auth_context.customer_id is None):
        return {
            "ok": False,
            "error": "auth_required",
            "message": "Authentication is required before shipment tools can be used.",
        }

    return tool.execute(arguments, shipment_repository, auth_context)
