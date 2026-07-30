"""LLM port: the interface business logic depends on.

Nothing in this module may import a concrete LLM SDK. Adapters
(e.g. LiteLLMClient) implement LLMClient; services only see this contract.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


class LLMError(Exception):
    """Raised by adapters when the underlying provider fails."""


class LLMClient(ABC):
    @abstractmethod
    async def plan_chat_turn(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> LLMCompletion:
        """Return one assistant response, optionally requesting tool calls."""
