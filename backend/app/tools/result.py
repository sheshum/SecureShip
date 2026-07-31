"""Structured result type for LLM tool responses.

All tools should return ToolResult instances to ensure consistent,
machine-readable responses that the LLM can reliably parse.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Structured response from an LLM tool execution.

    Attributes:
        success: True if the tool executed successfully, False on error
        message: Human-readable message for the LLM to interpret
        data: Optional structured data payload (dict) for complex responses

    Example:
        # Simple success
        ToolResult(success=True, message="Operation completed")

        # Success with data
        ToolResult(
            success=True,
            message="Found 2 shipments",
            data={"shipments": [...]}
        )

        # Error
        ToolResult(
            success=False,
            message="Invalid session state"
        )
    """

    success: bool
    message: str
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for LLM consumption.

        Returns:
            Dict with 'success', 'message', and optionally 'data' fields
        """
        result: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result
