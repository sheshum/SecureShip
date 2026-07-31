"""escalate_to_human tool - Escalate customer issues to a human operator.

This tool is designed to be used when the LLM determines that it cannot adequately
handle a customer's request or issue. It allows the LLM to flag the conversation for
human review, ensuring that the customer receives appropriate assistance.
"""

from app.tools.result import ToolResult
from app.tools.tool_registry import tool
from app.services.auth_context import AuthContext


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

    async def execute(
        self,
        _: AuthContext,
        issue_description: str,
    ) -> ToolResult:
        """Escalate the current customer issue to a human operator.

        Args:
            _: Authentication context (not used)
            issue_description: A brief description of the customer's issue or request

        Returns:
            ToolResult indicating that the escalation has been logged and will be reviewed by a human operator.
        """
        # Here you would implement the logic to log the escalation request,
        # notify a human operator, or take any other necessary actions.
        # For this example, we'll just return a success message.
        return ToolResult(
            success=True,
            message="The issue has been escalated to a human operator. A representative will review your request shortly.",
            issue_description=issue_description,
            issue_id="REQ-123456"  # In a real implementation, this would be a unique identifier for the escalation request
        )