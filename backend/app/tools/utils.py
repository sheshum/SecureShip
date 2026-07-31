"""Shared utility functions for tool handlers."""

import hashlib
import json
import logging
import random
from typing import Any

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


def log_console(message: str, data: Any = None, level: str = "INFO") -> None:
    """Print a log message with optional data to console.

    Args:
        message: The log message to print
        data: Optional data to include (dict, list, object, etc.)
        level: Log level - "DEBUG", "INFO", "WARNING", "ERROR" (default: "INFO")

    Example:
        log_console("Processing request", {"user_id": 123, "action": "verify"})
        log_console("Error occurred", error_details, level="ERROR")
    """
    logger = logging.getLogger(__name__)
    log_fn = getattr(logger, level.lower(), logger.info)

    if data is not None:
        # Format data as pretty JSON for readability
        try:
            data_str = json.dumps(data, indent=2, default=str)
            log_fn(f"{message}\n{data_str}")
        except (TypeError, ValueError):
            # Fallback to string representation if JSON serialization fails
            log_fn(f"{message}\n{data}")
    else:
        log_fn(message)
