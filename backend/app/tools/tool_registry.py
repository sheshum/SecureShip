"""
Every tool the model can call registers itself here, declaring up front
whether it requires a verified session. This registry — not the handler
bodies — is what Epic F3 points to.
"""

from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar

from app.models import ChatSession


class ToolHandler(Protocol):
    """Protocol for tool handler classes."""
    
    async def execute(
        self,
        session: ChatSession,
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


# Global tool registry - maps tool names to their specifications
TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(
    name: str,
    schema: dict[str, Any],
    handler: ToolHandler,
    requires_verification: bool,
) -> None:
    """Register a tool handler with its schema and verification requirement.
    
    No default for requires_verification, on purpose: every tool author
    has to make an explicit choice. This is a load-bearing design decision
    for Epic F — forgetting to register means the tool doesn't exist,
    and forgetting the verification flag is a loud error, not a silent leak.
    
    Note: With FastAPI DI, handlers are now constructed per-request via
    dependency injection. This function is called from get_tool_registry()
    with freshly constructed tool instances.
    """
    if name in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' is already registered")

    TOOL_REGISTRY[name] = ToolSpec(
        name=name,
        schema=schema,
        handler=handler,
        requires_verification=requires_verification,
    )


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
        return name, schema, requires_verification
    except AttributeError as e:
        raise AttributeError(
            f"Tool class {tool_class.__name__} must be decorated with @tool. "
            f"Missing attribute: {e}"
        ) from e
