"""The ONLY code path allowed to invoke a tool handler.

single auditable checkpoint: if this function isn't the one that ran,
the tool didn't run. Nothing else in the codebase calls a handler directly.
"""

import logging
from typing import Any

from app.services.auth_context import AuthContext
from app.services.identity_gate import enforce_gate
from app.tools.result import ToolResult, ToolStatus

logger = logging.getLogger(__name__)


async def dispatch_tool_call(
    context: AuthContext,
    fn_name: str,
    args: dict[str, Any],
    tool_registry: dict[str, Any],
) -> dict[str, Any]:
    """Execute a tool call after enforcing the verification gate.

    This is the single enforcement point for Epic F. Every tool call
    goes through here, and gated tools are blocked before their handler
    ever runs if the session is not verified.

    Args:
        context: Authentication context (contains verification state)
        fn_name: Name of the tool to call
        args: Arguments to pass to the tool handler
        tool_registry: The tool registry (injected per-request with fresh tool instances)

    Returns:
        Tool execution result dict (always ToolResult.to_dict() shape).
    """
    spec = tool_registry.get(fn_name)
    if spec is None:
        logger.warning(
            "Unknown tool call",
            extra={"session_id": str(context.session_id), "tool": fn_name},
        )
        return ToolResult(
            status=ToolStatus.ERROR,
            message=f"Unknown tool: {fn_name}",
        ).to_dict()

    # Epic F3: The gate check happens HERE, before any handler runs.
    # A tool that requires verification cannot execute without a verified session.
    if spec.requires_verification:
        gate_result = enforce_gate(context)
        if not gate_result.allowed:
            logger.warning(
                "Gate denied tool call",
                extra={
                    "session_id": str(context.session_id),
                    "tool": fn_name,
                    "state": context.state.value,
                },
            )
            return ToolResult(
                status=ToolStatus.ERROR,
                message="This tool is only available after identity verification.",
            ).to_dict()

    # Only verified tools OR public tools (requires_verification=False) reach this point.
    tool_result = await spec.handler.execute(context, **args)

    # Convert ToolResult to dict for JSON serialization
    if isinstance(tool_result, ToolResult):
        return tool_result.to_dict()

    # Backward compatibility: if tool still returns raw dict, pass through
    return tool_result
