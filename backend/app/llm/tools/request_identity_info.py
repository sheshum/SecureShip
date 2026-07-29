"""request_identity_info tool: schema + execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.tools import AuthContext
    from app.repositories.shipments import ShipmentRepository

TOOL_SCHEMA: dict[str, Any] = {
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
}


def execute(
    _: dict[str, Any],
    _shipment_repository: "ShipmentRepository",
    _auth_context: "AuthContext",
) -> dict[str, Any]:
    return {
        "ok": True,
        "action": "collect_identity",
        "required_fields": ["first_name", "last_name", "phone_number"],
        "message": "Please share your first name, last name, and phone number so I can verify your identity.",
    }