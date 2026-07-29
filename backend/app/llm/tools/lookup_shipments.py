"""lookup_shipments tool: schema + execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.tools import AuthContext
    from app.repositories.shipments import ShipmentRepository

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "lookup_shipments",
        "description": "Fetch all shipments for the verified customer in the active chat session.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


def execute(
    _: dict[str, Any],
    shipment_repository: "ShipmentRepository",
    auth_context: "AuthContext",
) -> dict[str, Any]:
    try:
        shipments = shipment_repository.get_shipments_for_customer(auth_context.customer_id)
    except Exception:
        return {
            "ok": False,
            "error": "lookup_shipments_failed",
            "message": "Unable to fetch shipments right now. Please try again.",
        }

    return {
        "ok": True,
        **shipments,
    }