from typing import Any

from app.models import Package, Shipment
from app.repositories.shipments import ShipmentRepository
from app.services.auth_context import AuthContext
from app.tools.result import ToolResult
from app.tools.tool_registry import tool


LOOKUP_SHIPMENTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_shipments",
        "description": (
            "Look up shipments for the customer. Can retrieve all "
            "shipments or filter by a specific tracking number."
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
}


@tool(
    name="lookup_shipments",
    schema=LOOKUP_SHIPMENTS_SCHEMA,
    requires_verification=True,
)
class LookupShipmentsTool:
    """Tool for looking up shipments for verified customers.
    """
    
    def __init__(self, shipment_repo: ShipmentRepository):
        self.shipment_repo = shipment_repo
    
    async def execute(
        self,
        context: AuthContext,
        tracking_number: str | None = None,
    ) -> ToolResult:
        """Look up shipments for the verified customer.
        
        Args:
            context: Authentication context (must be verified to reach this point)
            tracking_number: Optional filter for a specific tracking number
            
        Returns:
            ToolResult with shipment data, or empty array if no matches found
            (neutral response, no enumeration leak)
        """
        # Epic D2: customer_id comes from auth context (server-side, verified),
        # NEVER from tool arguments or LLM output.
        if context.customer_id is None:
            # This should never happen (dispatch_tool_call checks verification),
            # but fail closed defensively.
            return ToolResult(
                success=True,
                message="No shipments found",
                data={"shipments": []}
            )

        # Use repository to query shipments
        shipments = self.shipment_repo.list_shipments_for_customer(
            customer_id=context.customer_id,
            tracking_number=tracking_number,
        )

        # Epic D2: Empty array if no match (neutral, doesn't reveal whether
        # the tracking number exists for OTHER customers)
        shipment_count = len(shipments)
        message = f"Found {shipment_count} shipment{'s' if shipment_count != 1 else ''}" if shipment_count > 0 else "No shipments found"
        
        return ToolResult(
            success=True,
            message=message,
            data={"shipments": [_serialize_shipment(shipment) for shipment in shipments]}
        )


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
