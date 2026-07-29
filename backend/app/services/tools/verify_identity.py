"""
verify_identity tool - Verify customer identity and send OTP code.

This tool is the entry point to the verification flow. It:
1. Matches user-provided identity info (name + phone) against Customer table
2. Generates and sends a verification code if match found
3. Returns neutral responses to prevent enumeration attacks (SEC-13)
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatSession, Customer
from app.services.auth_session import AuthSessionData
from app.services.sms_mock import send_mock_sms
from app.services.tool_registry import register_tool
from app.services.tools.utils import OTP_EXPIRY_MINUTES, generate_otp, hash_code

@register_tool(
    name="verify_identity",
    schema={
        "type": "function",
        "function": {
            "name": "verify_identity",
            "description": (
                "Verify a customer's identity using their first name, last name, "
                "and phone number. If the information matches a customer in our system, "
                "a verification code will be sent to their phone number. "
                "The customer must then provide this code to complete verification."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {
                        "type": "string",
                        "description": "Customer's first name",
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Customer's last name",
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "Customer's phone number (e.g., +1234567890)",
                    },
                },
                "required": ["first_name", "last_name", "phone_number"],
            },
        },
    },
    requires_verification=False,  # This IS the verification flow
)
async def tool_verify_identity(
    db: AsyncSession,
    session: ChatSession,
    first_name: str,
    last_name: str,
    phone_number: str,
) -> dict[str, str]:
    """Verify customer identity and send OTP code.
    
    Epic B3 (SEC-13): Returns NEUTRAL responses regardless of whether
    the customer exists. Never reveals:
    - Whether a customer with that name exists
    - Which field didn't match
    - How many customers matched
    
    Security: The model never sees the actual OTP code - only whether
    one was sent. The code is hashed before storage.
    
    Args:
        db: Database session
        session: Chat session
        first_name: Customer's first name
        last_name: Customer's last name
        phone_number: Customer's phone number
        
    Returns:
        Neutral success or failure message (enumeration-proof)
    """
    # Import here to avoid circular dependency
    from app.services.tools import auth_store
    
    # Case-insensitive match against Customer table (name + phone)
    result = await db.execute(
        select(Customer).where(
            func.lower(Customer.first_name) == first_name.lower(),
            func.lower(Customer.last_name) == last_name.lower(),
            Customer.phone_number == phone_number,
        )
    )
    customer = result.scalar_one_or_none()

    # SEC-13: Same neutral response whether match succeeds or fails
    # This prevents enumeration attacks (attacker can't discover which
    # customers exist by trying different names/phones)
    
    if customer is None:
        # No match - but we return the SAME message as success
        return {
            "status": "pending",
            "message": "If that information matches our records, a verification code will be sent to your phone shortly.",
        }

    # Match found - generate and send OTP
    code = generate_otp()
    code_hash_value = hash_code(code)
    
    now = datetime.now(datetime.timezone.utc)
    expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Store OTP data in ephemeral auth session store (NOT in ChatSession)
    auth_store.set(
        session.id,
        AuthSessionData(
            session_id=session.id,
            code_hash=code_hash_value,
            sent_at=now,
            expires_at=expires_at,
            attempts=0,
            matched_customer_id=customer.id,
        ),
    )
    
    # Update ChatSession state to indicate code was sent
    session.state = "code_sent"
    await db.commit()
    
    # Send mock SMS (logs to console in dev, would be Twilio in prod)
    send_mock_sms(customer.phone_number, code)
    
    # Return SAME neutral message as failure case (SEC-13)
    # The model learns "code sent" but never learns the code itself
    return {
        "status": "pending",
        "message": "If that information matches our records, a verification code will be sent to your phone shortly.",
    }
