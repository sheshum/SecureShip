"""Chat request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.sessions import ChatSessionState


class ChatRequest(BaseModel):
    """A single chat request with a user prompt."""

    prompt: str = Field(..., min_length=1, description="User's message to the assistant")
    session_id: UUID | None = Field(
        None, description="Optional session ID to continue an existing conversation"
    )


class ChatResponse(BaseModel):
    """The assistant's reply."""

    reply: str = Field(..., description="Assistant's response text")
    session_id: UUID = Field(..., description="Session ID for this conversation")
    state: ChatSessionState = Field(..., description="Current session state")
    verification_required: bool | None = Field(
        None, description="Whether user verification is required (true when state is CODE_SENT)"
    )
