"""Result types for agent execution."""

from dataclasses import dataclass

from app.llm.base import LLMMessage


@dataclass(frozen=True)
class AgentResult:
    """Result of an agent turn execution.

    Attributes:
        reply: The assistant's final response
        messages: Full message list (including system, user, assistant, tool messages)
        tool_calls_made: Number of tool calls executed (for debugging)
    """

    reply: str
    messages: list[LLMMessage]
    tool_calls_made: int = 0
