"""get_shipment_status tool: schema + execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.tools import AuthContext
    from app.repositories.shipments import ShipmentRepository

TOOL_SCHEMA: dict[str, Any] = {
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
}


def execute(
    arguments: dict[str, Any],
    shipment_repository: "ShipmentRepository",
    auth_context: "AuthContext",
) -> dict[str, Any]:
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
            "ok": True,
            "found": False,
            "tracking_number": tracking_number,
        }

    return {
        "ok": True,
        "found": True,
        "shipment": shipment,
    }