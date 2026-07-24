"""LiteLLM adapter — the only module that talks to the litellm SDK."""

import logging
from collections.abc import AsyncIterator, Sequence

import litellm

from app.llm.base import LLMClient, LLMError, LLMMessage

logger = logging.getLogger(__name__)


class LiteLLMClient(LLMClient):
    def __init__(
        self,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._api_base = api_base
        self._api_key = api_key

    async def stream_chat(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]:
        try:
            stream = await litellm.acompletion(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                api_base=self._api_base,
                api_key=self._api_key,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.exception("LLM completion failed (model=%s)", self._model)
            raise LLMError("The language model is currently unavailable.") from exc
