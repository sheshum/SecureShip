"""Every tool the model can call declares up front, via the @tool decorator.

whether it requires a verified session. The dispatcher reads this at call time
via ToolRegistry — one instance is built per-request in
app.dependencies.get_tool_registry, so there is no shared mutable state.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

from app.services.auth_context import AuthContext


class ToolName(StrEnum):
    REQUEST_IDENTITY_INFO = "request_identity_info"
    START_IDENTITY_VERIFICATION = "start_identity_verification"
    LOOKUP_SHIPMENTS = "lookup_shipments"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class ToolHandler(Protocol):
    """Protocol for tool handler classes."""

    async def execute(
        self,
        context: AuthContext,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the tool with given arguments."""
        ...


@dataclass(frozen=True)
class ToolSpec:
    """Specification for a registered tool."""

    name: str
    schema: dict[str, Any]
    handler: ToolHandler
    requires_verification: bool


# Type variable for decorator
T = TypeVar("T", bound=type[ToolHandler])


def tool(
    name: str,
    schema: dict[str, Any],
    requires_verification: bool,
) -> Callable[[T], T]:
    """Decorator to attach tool metadata to a tool class.

    This decorator stores the tool's name, schema, and verification requirement
    as class attributes. The tool must still be instantiated and registered
    separately (allowing for dependency injection).

    Usage:
        @tool(
            name="lookup_shipments",
            schema=LOOKUP_SHIPMENTS_SCHEMA,
            requires_verification=True,
        )
        class LookupShipmentsTool:
            def __init__(self, shipment_repo: ShipmentRepository):
                self.shipment_repo = shipment_repo

            async def execute(self, session: ChatSession, **kwargs) -> dict:
                ...

        # Later, in __init__.py:
        tool_instance = LookupShipmentsTool(shipment_repo=ShipmentRepository())
        register_tool_instance(tool_instance)
    """

    def decorator(cls: T) -> T:
        cls._tool_name = name  # type: ignore
        cls._tool_schema = schema  # type: ignore
        cls._tool_requires_verification = requires_verification  # type: ignore
        return cls

    return decorator


class ToolRegistry:
    """Per-request registry of tool specs. Immutable after construction."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: ToolName) -> ToolSpec:
        """Typed accessor — raises KeyError with diagnostics if the tool is missing."""
        spec = self._tools.get(str(name))
        if spec is None:
            raise KeyError(f"Tool '{name}' is not registered. Available: {list(self._tools)}")
        return spec

    def find(self, name: str) -> ToolSpec | None:
        """Raw-name lookup for dispatch — returns None when the LLM calls an unknown tool."""
        return self._tools.get(name)


def get_tool_metadata(tool_class: type) -> tuple[str, dict[str, Any], bool]:
    """Extract tool metadata from a @tool decorated class.

    Args:
        tool_class: A class decorated with @tool

    Returns:
        Tuple of (name, schema, requires_verification)

    Raises:
        AttributeError: If the class wasn't decorated with @tool
    """
    try:
        name = tool_class._tool_name  # type: ignore
        schema = tool_class._tool_schema  # type: ignore
        requires_verification = tool_class._tool_requires_verification  # type: ignore
    except AttributeError as e:
        raise AttributeError(
            f"Tool class {tool_class.__name__} must be decorated with @tool. Missing attribute: {e}"
        ) from e
    else:
        return name, schema, requires_verification
