"""LLM tool definitions and execution helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.llm.base import ToolCall
from app.repositories.shipments import ShipmentRepository


@dataclass(frozen=True, slots=True)
class AuthContext:
    customer_id: UUID | None

    @property
    def is_verified(self) -> bool:
        return self.customer_id is not None

SHIPMENT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_shipment_status",
            "description": "Fetch a shipment by tracking number and return its current status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The shipment tracking number provided by the customer.",
                    }
                },
                "required": ["tracking_number"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_shipments",
            "description": "Fetch all shipments for the verified customer in the active chat session.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]

AUTH_GATE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "request_identity_info",
            "description": "Request identity fields required to verify a customer before shipment access.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_identity",
            "description": "Verify customer identity and start OTP challenge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {
                        "type": "string",
                    },
                    "last_name": {
                        "type": "string",
                    },
                    "phone_number": {
                        "type": "string",
                    },
                },
                "required": ["first_name", "last_name", "phone_number"],
                "additionalProperties": False,
            },
        },
    },
]


def execute_tool_call(
    tool_call: ToolCall,
    shipment_repository: ShipmentRepository,
    auth_context: AuthContext,
) -> dict[str, Any]:
    try:
        arguments = json.loads(tool_call.arguments or "{}")
    except json.JSONDecodeError:
        arguments = {}

    if not auth_context.is_verified or auth_context.customer_id is None:
        return {
            "ok": False,
            "error": "auth_required",
            "message": "Authentication is required before shipment tools can be used.",
        }

    if tool_call.name == "get_shipment_status":
        tracking_number = str(arguments.get("tracking_number", "")).strip()
        if not tracking_number:
            return {
                "ok": False,
                "error": "tracking_number is required",
            }
        shipment = shipment_repository.get_shipment_by_tracking_number_for_customer(
            tracking_number,
            auth_context.customer_id,
        )
        if shipment is None:
            return {
                "ok": False,
                "found": False,
                "tracking_number": tracking_number,
            }
        return {
            "ok": True,
            "found": True,
            "shipment": shipment,
        }

    if tool_call.name == "get_my_shipments":
        return {
            "ok": True,
            **shipment_repository.get_shipments_for_customer(auth_context.customer_id),
        }

    return {
        "ok": False,
        "error": f"Unknown tool: {tool_call.name}",
    }