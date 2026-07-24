"""LLM port: the interface business logic depends on.

Nothing in this module may import a concrete LLM SDK. Adapters
(e.g. LiteLLMClient) implement LLMClient; services only see this contract.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMError(Exception):
    """Raised by adapters when the underlying provider fails."""


class LLMClient(ABC):
    @abstractmethod
    def stream_chat(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        """Send a conversation to the model and yield response text deltas."""
