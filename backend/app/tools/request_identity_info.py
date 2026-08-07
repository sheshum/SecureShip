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
            "Signal that identity information (first name, last name, phone number) "
            "must be collected from the customer before verification can start. "
            "Call this exactly once at the beginning of the verification workflow, "
            "before the customer has provided those fields. Do not call this after "
            "the customer has provided the fields — call start_identity_verification instead."
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
    the assistant should relay verbatim, asking the customer for the three
    identity fields.
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
            status=ToolStatus.SUCCESS,
            message=(
                "To help you with shipment information, I need to verify your identity. "
                "Could you please share your first name, last name, and phone number?"
            ),
        )
