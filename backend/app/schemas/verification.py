"""Schemas for verification endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class VerifyCodeRequest(BaseModel):
    """Request to verify an OTP code."""

    code: str = Field(..., min_length=6, max_length=6, description="The 6-digit OTP code")


class VerifyCodeResponse(BaseModel):
    """Response from code verification attempt."""

    result: Literal["verified", "incorrect", "expired"] = Field(..., description="Verification result status")
    attempts_remaining: int | None = Field(
        None, description="Number of attempts remaining (only for 'incorrect' result)"
    )
