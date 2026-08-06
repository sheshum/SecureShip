"""verify_identity tool - Verify customer identity and send OTP code.

This tool is the entry point to the verification flow. It:
1. Matches user-provided identity info (name + phone) against Customer table
2. Generates and sends a verification code if match found
3. Returns neutral responses to prevent enumeration attacks (SEC-13)
"""

from datetime import UTC, datetime, timedelta

from app.repositories.chat_sessions import ChatSessionRepository
from app.repositories.customers import CustomerRepository
from app.repositories.session_verification import SessionVerificationRepository
from app.schemas.sessions import ChatSessionState
from app.services.auth_context import AuthContext
from app.services.sms_mock import send_mock_sms
from app.tools.result import ToolResult, ToolStatus
from app.tools.tool_registry import tool
from app.tools.utils import OTP_EXPIRY_MINUTES, generate_otp, hash_code, log_console

VERIFY_IDENTITY_SCHEMA = {
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
}


@tool(
    name="verify_identity",
    schema=VERIFY_IDENTITY_SCHEMA,
    requires_verification=False,
)
class VerifyIdentityTool:
    """Tool for verifying customer identity and sending OTP codes.

    Dependencies are injected via constructor to enable proper testing
    and follow the repository pattern used throughout the codebase.
    """

    def __init__(
        self,
        customer_repo: CustomerRepository,
        session_repo: ChatSessionRepository,
        verification_repo: SessionVerificationRepository,
    ):
        self.customer_repo = customer_repo
        self.session_repo = session_repo
        self.verification_repo = verification_repo

    async def execute(
        self,
        context: AuthContext,
        first_name: str,
        last_name: str,
        phone_number: str,
    ) -> ToolResult:
        """Verify customer identity and send OTP code.

        Args:
            context: Authentication context
            first_name: Customer's first name
            last_name: Customer's last name
            phone_number: Customer's phone number

        Returns:
            ToolResult with neutral success or failure message (enumeration-proof)
        """
        if context.state != ChatSessionState.ANONYMOUS and context.state != ChatSessionState.COLLECTING_IDENTITY:
            # This should never happen (dispatch_tool_call checks verification)
            log_console(
                f"verify_identity: session {context.session_id} is not ANONYMOUS, state={context.state}"
            )
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Already verified. Identity verification cannot be performed in the current session state.",
            )

        # Use repository to find customer by identity
        customer = self.customer_repo.find_by_identity(first_name, last_name, phone_number)

        log_console(
            "verify identity: got customer match: "
            + (f"customer_id={customer.id}" if customer else "no match")
        )

        if customer is None:
            # No match - but we return success=True (enumeration-proof)
            return ToolResult(status=ToolStatus.SUCCESS, message="Identity verification failed.")

        # Match found - generate and send OTP
        code = generate_otp()
        code_hash_value = hash_code(code)

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

        log_console(
            f"verify_identity: generated OTP code={code} (hashed) for customer_id={customer.id}, expires_at={expires_at.isoformat()}"
        )
        self.verification_repo.create(
            session_id=context.session_id,
            code_hash=code_hash_value,
            matched_customer_id=customer.id,
            sent_at=now,
            expires_at=expires_at,
        )

        self.session_repo.update_session(context.session_id, state=ChatSessionState.CODE_SENT)

        # Send mock SMS (logs to console in dev, would be Twilio in prod)
        send_mock_sms(customer.phone_number, code)

        # Return SAME neutral message as failure case (SEC-13)
        # The model learns "code sent" but never learns the code itself
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message="If that information matches our records, a verification code will be sent to your phone shortly.",
            data={"verification_status": "code_sent"},
        )
