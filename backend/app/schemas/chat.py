"""Chat request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A single chat request with a user prompt."""

    prompt: str = Field(..., min_length=1, description="User's message to the assistant")


class ChatResponse(BaseModel):
    """The assistant's reply."""

    reply: str = Field(..., description="Assistant's response text")
