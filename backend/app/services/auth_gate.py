from uuid import UUID

from app.repositories.chat_sessions import ChatSessionRepository
from app.services.identity_verification import IdentityVerificationService
from app.services.otp import OtpService
from app.services.sms import SmsService


class AuthGateService:
    def __init__(
        self,
        identity_service: IdentityVerificationService,
        otp_service: OtpService,
        sms_service: SmsService,
        session_repository: ChatSessionRepository,
    ) -> None:
        self._identity_service = identity_service
        self._otp_service = otp_service
        self._sms_service = sms_service
        self._session_repository = session_repository

    def execute_tool_call(self, tool_name: str, tool_args: dict, session_id: UUID) -> dict:
        if tool_name == "request_identity_info":
            return {
                "ok": True,
                "action": "collect_identity",
                "required_fields": ["first_name", "last_name", "phone_number"],
                "message": "Please share your first name, last name, and phone number so I can verify your identity.",
            }

        if tool_name != "verify_identity":
            return {
                "ok": False,
                "error": f"Unknown tool: {tool_name}",
            }

        first_name = str(tool_args.get("first_name") or "").strip()
        last_name = str(tool_args.get("last_name") or "").strip()
        phone_number = str(tool_args.get("phone_number") or "").strip()

        if not first_name or not last_name or not phone_number:
            return {
                "ok": False,
                "started": False,
                "show_code_modal": False,
                "state": "collecting_identity",
                "message": "I still need first name, last name, and phone number to verify your identity.",
                "error_code": "missing_identity_fields",
            }

        identity = self._identity_service.verify_identity(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        if not identity.matched or identity.match is None:
            self._session_repository.update_auth_state(
                session_id,
                state="collecting_identity",
                customer_id=None,
            )
            return {
                "ok": False,
                "started": False,
                "show_code_modal": False,
                "state": "collecting_identity",
                "message": "We could not verify your identity. Please check your details and try again.",
                "error_code": "identity_no_match",
            }

        pending_customer_id = UUID(identity.match.customer_id)
        otp_issue = self._otp_service.issue_code(
            session_id,
            pending_customer_id=pending_customer_id,
        )
        if not otp_issue.ok:
            return {
                "ok": False,
                "started": False,
                "show_code_modal": False,
                "state": "awaiting_code",
                "message": "Please wait before requesting another verification code.",
                "error_code": otp_issue.error_code,
                "retry_at": (
                    otp_issue.retry_at.isoformat().replace("+00:00", "Z")
                    if otp_issue.retry_at is not None
                    else None
                ),
            }

        self._sms_service.send_otp(phone_number, otp_issue.otp_code or "")
        self._session_repository.update_auth_state(
            session_id,
            state="code_sent",
            customer_id=None,
        )
        return {
            "ok": True,
            "started": True,
            "show_code_modal": True,
            "state": "code_sent",
            "message": "Verification code sent. Enter the code to continue.",
        }
