"""LLM tool definitions and execution helpers."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.llm.base import ToolCall
from app.repositories.shipments import ShipmentRepository

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
            "name": "get_shipment_by_user",
            "description": "Fetch all shipments for a customer/user identifier extracted from the request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer identifier extracted from the user's message.",
                    }
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    },
]


def execute_tool_call(
    tool_call: ToolCall,
    shipment_repository: ShipmentRepository,
) -> dict[str, Any]:
    arguments = json.loads(tool_call.arguments or "{}")

    if tool_call.name == "get_shipment_status":
        tracking_number = str(arguments.get("tracking_number", "")).strip()
        if not tracking_number:
            return {
                "ok": False,
                "error": "tracking_number is required",
            }
        shipment = shipment_repository.get_shipment_by_tracking_number(tracking_number)
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

    if tool_call.name == "get_shipment_by_user":
        user_id = str(arguments.get("user_id", "")).strip()
        if not user_id:
            return {
                "ok": False,
                "error": "user_id is required",
            }
        try:
            UUID(user_id)
        except ValueError:
            return {
                "ok": False,
                "error": "user_id must be a valid UUID",
                "user_id": user_id,
            }
        try:
            return {
                "ok": True,
                **shipment_repository.get_shipments_by_customer_id(user_id),
            }
        except ValueError:
            return {
                "ok": False,
                "error": "user_id must be a valid UUID",
                "user_id": user_id,
            }

    return {
        "ok": False,
        "error": f"Unknown tool: {tool_call.name}",
    }