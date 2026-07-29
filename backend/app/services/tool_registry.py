"""
Every tool the model can call registers itself here, declaring up front
whether it requires a verified session. This registry — not the handler
bodies — is what Epic F3 points to.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    """Specification for a registered tool."""

    name: str
    schema: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]]
    requires_verification: bool


# Global registry of all tools the LLM can invoke.
# Key: tool name, Value: ToolSpec
TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(
    *,
    name: str,
    schema: dict[str, Any],
    requires_verification: bool,
) -> Callable[[Callable[..., Awaitable[dict[str, Any]]]], Callable[..., Awaitable[dict[str, Any]]]]:
    """Register a tool handler with its schema and verification requirement.
    
    No default for requires_verification, on purpose: every tool author
    has to make an explicit choice. This is a load-bearing design decision
    for Epic F — forgetting to add this decorator means the tool doesn't
    get registered at all, so it can't be called. Forgetting the verification
    flag is a loud compile-time error, not a silent runtime leak.
    
    Usage:
        @register_tool(
            name="my_tool",
            schema={"type": "function", "function": {...}},
            requires_verification=True,
        )
        async def tool_my_tool(db, session, **args):
            ...
    """

    def decorator(
        handler: Callable[..., Awaitable[dict[str, Any]]]
    ) -> Callable[..., Awaitable[dict[str, Any]]]:
        if name in TOOL_REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered")

        TOOL_REGISTRY[name] = ToolSpec(
            name=name,
            schema=schema,
            handler=handler,
            requires_verification=requires_verification,
        )
        return handler

    return decorator
