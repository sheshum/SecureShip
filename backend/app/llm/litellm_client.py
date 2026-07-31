"""LiteLLM adapter — the only module that talks to the litellm SDK."""

import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

import litellm

from app.llm.base import LLMClient, LLMCompletion, LLMError, LLMMessage, ToolCall

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

    async def plan_chat_turn(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        tool_choice: str | list[str] | dict[str, Any] | None = None,
    ) -> LLMCompletion:
        try:
            resolved_tool_choice = self._resolve_tool_choice(tool_choice, tools)
            response = await litellm.acompletion(
                model=self._model,
                messages=self._serialize_messages(messages),
                api_base=self._api_base,
                api_key=self._api_key,
                tools=list(tools) if tools else None,
                tool_choice=resolved_tool_choice,
                stream=False,
            )
            choice = response.choices[0]
            message = choice.message
            tool_calls = tuple(
                ToolCall(
                    id=self._tool_call_id(tool_call),
                    name=self._tool_call_name(tool_call),
                    arguments=self._tool_call_arguments(tool_call),
                )
                for tool_call in (getattr(message, "tool_calls", None) or [])
            )
            content = getattr(message, "content", "") or ""
            return LLMCompletion(content=str(content), tool_calls=tool_calls)
        except Exception as exc:
            logger.exception("LLM completion failed (model=%s)", self._model)
            raise LLMError("The language model is currently unavailable.") from exc

    @staticmethod
    def _resolve_tool_choice(
        tool_choice: str | list[str] | dict[str, Any] | None,
        tools: Sequence[dict[str, Any]] | None,
    ) -> str | dict[str, Any] | None:
        """Convert tool_choice to OpenAI format.
        
        Args:
            tool_choice: User-provided tool choice (string, list, dict, or None)
            tools: Available tools
            
        Returns:
            OpenAI-formatted tool_choice or None
        """
        if not tools:
            return None
            
        if tool_choice is None:
            return "auto"
            
        if isinstance(tool_choice, dict):
            return tool_choice
            
        # Convert string or list to OpenAI format
        tool_name = tool_choice if isinstance(tool_choice, str) else tool_choice[0]
        return tool_name


    @staticmethod
    def _serialize_messages(messages: Sequence[LLMMessage]) -> list[dict[str, Any]]:
        serialized_messages: list[dict[str, Any]] = []
        for message in messages:
            payload: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.tool_call_id:
                payload["tool_call_id"] = message.tool_call_id
            if message.tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        },
                    }
                    for tool_call in message.tool_calls
                ]
            serialized_messages.append(payload)
        return serialized_messages

    @staticmethod
    def _tool_call_id(tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            return str(tool_call.get("id", ""))
        return str(getattr(tool_call, "id", ""))

    @staticmethod
    def _tool_call_name(tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            function = tool_call.get("function", {})
            return str(function.get("name", ""))
        function = getattr(tool_call, "function", None)
        return str(getattr(function, "name", ""))

    @staticmethod
    def _tool_call_arguments(tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            function = tool_call.get("function", {})
            return str(function.get("arguments", ""))
        function = getattr(tool_call, "function", None)
        return str(getattr(function, "arguments", ""))
