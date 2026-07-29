"""
LLM tool handlers. Each tool is defined in its own module.

This package imports all tools to trigger their registration with the
tool registry. The tools themselves declare whether they require verification.
"""

from app.services.auth_session import InMemoryAuthSessionStore

# Global auth session store (in-memory for now, Redis later)
# Shared across all tools that need OTP verification
auth_store = InMemoryAuthSessionStore()

# Import all tools to trigger registration
# (The @register_tool decorator runs on import, adding tools to TOOL_REGISTRY)
from app.services.tools.verify_identity import tool_verify_identity

__all__ = ["auth_store", "tool_verify_identity"]
