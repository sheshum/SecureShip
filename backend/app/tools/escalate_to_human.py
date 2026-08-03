"""escalate_to_human tool - Escalate customer issues to a human operator.

This tool is designed to be used when the LLM determines that it cannot adequately
handle a customer's request or issue. It allows the LLM to flag the conversation for
human review, ensuring that the customer receives appropriate assistance.
"""

from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import ChatSessionState
from app.tools.result import ToolResult
from app.tools.tool_registry import tool
from app.services.auth_context import AuthContext

from logging import getLogger

logger = getLogger(__name__)

ESCALATE_TO_HUMAN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "escalate_to_human",
        "description": (
            "Escalate the current customer issue to a human operator. "
            "This should be used when the LLM cannot adequately handle the request, "
            "when the issue requires human judgment or intervention, "
            "or if the customer explicitly requests to speak with a human."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "issue_description": {
                    "type": "string",
                    "description": (
                        "A brief description of the customer's issue or request that "
                        "needs to be escalated to a human operator."
                    ),
                }
            },
            "required": ["issue_description"],
        },
    },
}
@tool(
    name="escalate_to_human",
    schema=ESCALATE_TO_HUMAN_SCHEMA,
    requires_verification=False
)
class EscalateToHumanTool:
    """Tool for escalating customer issues to a human operator.

    This tool is intended to be used when the LLM determines that it cannot
    adequately handle a customer's request or issue. It allows the LLM to flag
    the conversation for human review, ensuring that the customer receives
    appropriate assistance.
    """

    def __init__(self, session_repo: ChatSessionRepository):
        """Initialize with session repository dependency."""
        self.session_repo = session_repo

    async def execute(
        self,
        context: AuthContext,
        issue_description: str,
    ) -> ToolResult:
        """Escalate the current customer issue to a human operator.

        Args:
            context: Authentication context (contains session_id)
            issue_description: A brief description of the customer's issue or request

        Returns:
            ToolResult indicating that the escalation has been logged and will be reviewed by a human operator.
        """
        # Update session state to ESCALATED_TO_HUMAN
        logger.info(f"Escalating session {context.session_id} to human operator. Issue: {issue_description}")
        self.session_repo.update_session(
            context.session_id,
            state=ChatSessionState.ESCALATED_TO_HUMAN
        )
        
        # Here you would implement the logic to log the escalation request,
        # notify a human operator, or take any other necessary actions.
        # For this example, we'll just return a success message.
        mock_request_id = "REQ-123456"  # In a real implementation, this would be a unique identifier for the escalation request
        return ToolResult(
            success=True,
            message=f"The issue has been escalated to a human operator. A representative will review your request shortly. Your request id: {mock_request_id}. "
                    "Thank you for your patience.",
            data={
                "issue_description": issue_description,
                "issue_id": mock_request_id  # In a real implementation, this would be a unique identifier for the escalation request
            }
        )