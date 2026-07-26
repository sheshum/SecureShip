from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class ChatRequest(BaseModel):
    session_id: UUID
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=100)
