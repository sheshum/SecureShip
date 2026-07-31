"""Mock SMS service for development and testing.

Never sends actual SMS messages. Logs the verification code to console
so developers can complete the OTP flow during local testing.

In production, swap this for a real SMS provider (Twilio, AWS SNS, etc.)
without changing the calling code.
"""

import logging

logger = logging.getLogger(__name__)


def send_mock_sms(phone_number: str, code: str) -> None:
    """Log a verification code instead of sending SMS.

    Args:
        phone_number: The recipient's phone number
        code: The 6-digit verification code

    Security note: This function logs the raw code for dev convenience.
    In production SMS sending, the code should NEVER be logged - only
    success/failure metadata.
    """
    logger.info(
        "📱 MOCK SMS to %s: Your SecureShip verification code is %s",
        phone_number,
        code,
    )
    # In production, replace above with:
    # twilio_client.messages.create(to=phone_number, body=f"Your code: {code}")
    # And log only: logger.info("SMS sent to %s", mask_phone(phone_number))
