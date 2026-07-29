from typing import Any

from app.services.auth_context import AuthContext
from app.tools.tool_registry import tool


REQUEST_IDENTITY_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "request_identity_info",
        "description": (
            "Request identity verification from the user. Call this when you need "
            "to access customer data but the user hasn't verified their identity yet. "
            "Returns instructions to display to the user about the verification process."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


@tool(
    name="request_identity_info",
    schema=REQUEST_IDENTITY_INFO_SCHEMA,
    requires_verification=False,  # Public tool - can be called anytime
)
class RequestIdentityInfoTool:
    """Tool for requesting user identity verification.
    
    This tool is public (doesn't require verification) and returns a message
    explaining that the user needs to verify their identity to access
    customer data.
    """
    
    async def execute(
        self,
        _: AuthContext,
    ) -> dict[str, Any]:
        """Return a message requesting user verification.
        
        Args:
            context: Authentication context (verification state doesn't matter)
            
        Returns:
            {"message": "..."} with instructions for the user
        """
        return {
            "message": (
                "I need to verify your identity before I can access your shipment information. "
                "Please provide your first name, last name, and phone number to begin the verification process."
            )
        }
