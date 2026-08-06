"""Structured result type for LLM tool responses.

All tools should return ToolResult instances to ensure consistent,
machine-readable responses that the LLM can reliably parse.
"""

from dataclasses import dataclass
from typing import Any
from enum import Enum

class ToolStatus(str, Enum):
    SUCCESS = "success"
    NEEDS_USER_INPUT = "needs_user_input"
    ERROR = "error"

@dataclass
class ToolResult:
    """Structured response from an LLM tool execution.

    Attributes:
        status: ToolStatus indicating the result of the tool execution
        message: Human-readable message for the LLM to interpret
        data: Optional structured data payload (dict) for complex responses

    Example:
        # Simple success
        ToolResult(status=ToolStatus.SUCCESS, message="Operation completed")

        # Success with data
        ToolResult(
            status=ToolStatus.SUCCESS,
            message="Found 2 shipments",
            data={"shipments": [...]}
        )

        # Error
        ToolResult(
            status=ToolStatus.ERROR,
            message="Invalid session state"
        )
    """

    status: ToolStatus
    message: str
    action_required: str | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for LLM consumption.

        Returns:
            Dict with 'status', 'message', 'action_required', and optionally 'data' fields
        """
        result: dict[str, Any] = {
            "status": self.status.value,
            "message": self.message,
        }
        if self.action_required is not None:
            result["action_required"] = self.action_required
        if self.data is not None:
            result["data"] = self.data
        return result
