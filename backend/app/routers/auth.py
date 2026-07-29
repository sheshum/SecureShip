"""Authentication and verification endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# TODO: Implement auth/OTP endpoints (SEC-14+)
