"""Tool for requesting user identity verification."""
from logging import getLogger

from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import ChatSessionState
from app.services.auth_context import AuthContext
from app.tools.result import ToolResult, ToolStatus
from app.tools.tool_registry import tool

logger = getLogger(__name__)

REQUEST_IDENTITY_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "request_identity_info",
        "description": (
            "Start the identity verification workflow for an unverified customer. "
            "Call this tool when the user requests customer-specific information "
            "(for example shipment status, orders, account details) and their identity "
            "has not been verified yet. "
            "This is the required first step before accessing protected customer data. "
            "After calling this tool, wait for the user to provide the requested "
            "identity information. Do not attempt to access customer data or call "
            "other customer data tools until verification is completed."
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
    customer data. It sets the tool status to NEEDS_USER_INPUT.
    """

    def __init__(self, session_repo: ChatSessionRepository):
        self.session_repo = session_repo

    async def execute(
        self,
        context: AuthContext,
    ) -> ToolResult:
        """Return a message requesting user verification.

        Args:
            context: Authentication context (verification state doesn't matter)

        Returns:
            ToolResult with instructions for the user
        """
        logger.info("Requesting identity info for session %s", context.session_id)
        self.session_repo.update_session(
            context.session_id,
            state=ChatSessionState.COLLECTING_IDENTITY,
        )
        return ToolResult(
            status=ToolStatus.NEEDS_USER_INPUT,
            action_required="COLLECT_IDENTITY_INFO",
            message="User must provide their first name, last name, and phone number to begin the verification process.",
            data={
                "required_fields": ["first_name", "last_name", "phone_number"],
            }
        )
