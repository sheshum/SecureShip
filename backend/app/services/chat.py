"""Chat business logic. Depends only on the LLM port, never on a concrete SDK."""

from collections.abc import AsyncIterator, Sequence

from app.llm.base import LLMClient, LLMMessage

SYSTEM_PROMPT = (
    "You are the SecureShip assistant. You help customers with questions about "
    "their shipments, tracking, and deliveries. Be concise and friendly. "
    "If you don't know something, say so instead of guessing."
)


class ChatService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def stream_reply(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        """Yield the assistant's reply to the conversation as text deltas."""
        conversation = [LLMMessage(role="system", content=SYSTEM_PROMPT), *messages]
        return self._llm_client.stream_chat(conversation)
