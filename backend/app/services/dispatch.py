"""
The ONLY code path allowed to invoke a tool handler. This is Epic F3's
single auditable checkpoint: if this function isn't the one that ran,
the tool didn't run. Nothing else in the codebase calls a handler directly.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatSession
from app.services.identity_gate import enforce_gate
from app.services.tool_registry import TOOL_REGISTRY


async def dispatch_tool_call(
    db: AsyncSession,
    session: ChatSession,
    fn_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Execute a tool call after enforcing the verification gate.
    
    This is the single enforcement point for Epic F. Every tool call
    goes through here, and gated tools are blocked before their handler
    ever runs if the session is not verified.
    
    Args:
        db: Database session
        session: Chat session (contains verification state)
        fn_name: Name of the tool to call
        args: Arguments to pass to the tool handler
        
    Returns:
        Tool execution result dict, or {"error": "..."} on failure
    """
    spec = TOOL_REGISTRY.get(fn_name)
    if spec is None:
        return {"error": f"unknown_tool: {fn_name}"}

    # Epic F3: The gate check happens HERE, before any handler runs.
    # A tool that requires verification cannot execute without a verified session.
    if spec.requires_verification:
        gate_result = enforce_gate(session)
        if not gate_result.allowed:
            return {"error": "not_verified"}

    # Only verified tools OR public tools (requires_verification=False) reach this point.
    return await spec.handler(db, session, **args)
