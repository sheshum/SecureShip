"""verify_identity tool schema.

Execution for this tool is performed in the chat router where identity and OTP
services are available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.tools import AuthContext
    from app.repositories.shipments import ShipmentRepository

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "verify_identity",
        "description": "Verify customer identity and start OTP challenge.",
        "parameters": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "phone_number": {"type": "string"},
            },
            "required": ["first_name", "last_name", "phone_number"],
            "additionalProperties": False,
        },
    },
}


def execute(
    arguments: dict[str, Any],
    _shipment_repository: "ShipmentRepository",
    _auth_context: "AuthContext",
) -> dict[str, Any]:
    return {
        "ok": True,
        "identity": {
            "first_name": str(arguments.get("first_name") or "").strip(),
            "last_name": str(arguments.get("last_name") or "").strip(),
            "phone_number": str(arguments.get("phone_number") or "").strip(),
        },
    }
