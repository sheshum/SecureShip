"""Shared utility functions for tool handlers."""

import hashlib
import random

# OTP configuration constants
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_VERIFICATION_ATTEMPTS = 3


def generate_otp() -> str:
    """Generate a random 6-digit OTP code."""
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


def hash_code(code: str) -> str:
    """Hash an OTP code using SHA-256.
    
    Why hash: Even in mock/dev, storing raw codes next to customer PII
    is a bad habit to form. Hash it, then verify by hashing the user's
    input and comparing hashes.
    """
    return hashlib.sha256(code.encode()).hexdigest()
