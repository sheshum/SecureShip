"""Registry abstractions for LLM tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal

if TYPE_CHECKING:
    from app.llm.tools import AuthContext
    from app.repositories.shipments import ShipmentRepository

ToolGroup = Literal["shipment", "auth_gate"]
ToolExecutor = Callable[[dict[str, Any], "ShipmentRepository", "AuthContext"], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    name: str
    schema: dict[str, Any]
    execute: ToolExecutor
    requires_verified_auth: bool
    group: ToolGroup


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistration] = {}

    def register(self, tool: ToolRegistration) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolRegistration | None:
        return self._tools.get(name)

    def schemas_for_group(self, group: ToolGroup) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values() if tool.group == group]