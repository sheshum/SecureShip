"""
LLM tool handlers. Each tool is defined in its own module.

This package instantiates all tools with their dependencies and registers
them with the tool registry. Tools are class-based to support dependency
injection of repositories.
"""

from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.repositories.shipments import ShipmentRepository
from app.services.auth_session import InMemoryAuthSessionStore
from backend.app.tools.tool_registry import register_tool
from app.services.tools.lookup_shipments import (
    LOOKUP_SHIPMENTS_SCHEMA,
    LookupShipmentsTool,
)
from app.services.tools.verify_identity import (
    VERIFY_IDENTITY_SCHEMA,
    VerifyIdentityTool,
)

# Global auth session store (in-memory for now, Redis later)
# Shared across all tools that need OTP verification
auth_store = InMemoryAuthSessionStore()

# Instantiate tools with their dependencies
# Repositories create their own DB sessions, but tools also receive
# the current session from dispatch_tool_call for reading session state
verify_identity_tool = VerifyIdentityTool(
    customer_repo=CustomerRepository(),
    session_repo=ChatSessionRepository(),
    auth_store=auth_store,
)

lookup_shipments_tool = LookupShipmentsTool(
    shipment_repo=ShipmentRepository(),
)

# Register tools with the global registry
register_tool(
    name="verify_identity",
    schema=VERIFY_IDENTITY_SCHEMA,
    handler=verify_identity_tool,
    requires_verification=False,  # This IS the verification flow
)

register_tool(
    name="lookup_shipments",
    schema=LOOKUP_SHIPMENTS_SCHEMA,
    handler=lookup_shipments_tool,
    requires_verification=True,  # Epic F3: Single enforcement point
)

__all__ = [
    "auth_store",
    "verify_identity_tool",
    "lookup_shipments_tool",
]
