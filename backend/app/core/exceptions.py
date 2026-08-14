"""Application-level exceptions used across multiple layers."""


class SessionExpiredError(Exception):
    """Raised when a session cookie references an expired or non-existent session.

    Handled globally in main.py: returns 410 Gone and deletes the session cookie.
    """
