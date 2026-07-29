"""
lookup_shipments tool - Look up shipments for a verified customer.

SEC-19 / Epic D: This tool enforces two critical security boundaries:

1. Verification gate (D1): registered with requires_verification=True, so
   dispatch_tool_call blocks execution for unverified sessions.

2. Customer-scoped queries (D2): ALL queries filter by session.customer_id.
   A verified user requesting a tracking number that belongs to someone else
   gets an empty result, not an error. This prevents enumeration attacks.

Authorization is enforced by dispatch_tool_call + the customer_id filter,
never by examining tool arguments or trusting the LLM's judgment.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ChatSession, Shipment
from app.services.tool_registry import register_tool


@register_tool(
    name="lookup_shipments",
    schema={
        "type": "function",
        "function": {
            "name": "lookup_shipments",
            "description": (
                "Look up shipments for the verified customer. Can retrieve all "
                "shipments or filter by a specific tracking number. Only returns "
                "shipments belonging to the customer in this session."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": (
                            "Optional: Specific tracking number to look up. "
                            "If omitted, returns all shipments for the customer."
                        ),
                    }
                },
            },
        },
    },
    requires_verification=True,  # Epic F3: Single enforcement point
)
async def tool_lookup_shipments(
    db: AsyncSession,
    session: ChatSession,
    tracking_number: str | None = None,
) -> dict[str, Any]:
    """Look up shipments for the verified customer.
    
    Epic D2: Authorization boundary is session.customer_id, not arguments.
    This handler can only run if dispatch_tool_call allowed it (verified session).
    
    Args:
        db: Database session
        session: Chat session (must be verified to reach this point)
        tracking_number: Optional filter for a specific tracking number
        
    Returns:
        {"shipments": [...]} with flattened shipment data, or empty array
        if no matches found (neutral response, no enumeration leak)
    """
    # Epic D2: customer_id comes from session state (server-side, verified),
    # NEVER from tool arguments or LLM output.
    if session.customer_id is None:
        # This should never happen (dispatch_tool_call checks verification),
        # but fail closed defensively.
        return {"shipments": []}

    # Build query: always scope by customer_id first
    stmt = (
        select(Shipment)
        .options(selectinload(Shipment.packages))
        .where(Shipment.customer_id == session.customer_id)
    )

    # Optional tracking number filter
    if tracking_number:
        stmt = stmt.where(Shipment.tracking_number == tracking_number)

    # Order by most recent first
    stmt = stmt.order_by(Shipment.last_update.desc())

    result = await db.execute(stmt)
    shipments = result.scalars().all()

    # Epic D2: Empty array if no match (neutral, doesn't reveal whether
    # the tracking number exists for OTHER customers)
    return {
        "shipments": [_serialize_shipment(shipment) for shipment in shipments]
    }


def _serialize_shipment(shipment: Shipment) -> dict[str, Any]:
    """Serialize shipment to a flattened, LLM-friendly format.
    
    Only includes relevant, non-sensitive data:
    - Tracking number, status, carrier (operational info)
    - Origin, destination, estimated delivery (customer-visible)
    - Package count and descriptions (what they're expecting)
    
    Excludes:
    - Internal IDs (customer_id, shipment.id, package.id)
    - Declared values (sensitive financial data)
    - Weight (internal operational data)
    """
    # Flatten package data to simple descriptions
    package_descriptions = [pkg.description for pkg in shipment.packages]
    
    return {
        "tracking_number": shipment.tracking_number,
        "status": shipment.status,
        "carrier": shipment.carrier,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "estimated_delivery": shipment.estimated_delivery.isoformat(),
        "last_update": shipment.last_update.isoformat(),
        "package_count": len(shipment.packages),
        "package_descriptions": package_descriptions,
    }
