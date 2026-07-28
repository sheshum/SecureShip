from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class SmsSendResult:
    ok: bool
    provider: str
    masked_phone_number: str


class SmsProvider(Protocol):
    def send_sms(self, phone_number: str, message: str) -> SmsSendResult: ...


class ConsoleSmsProvider:
    def __init__(self, output: Callable[[str], None] | None = None) -> None:
        self._output = output or print

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        masked_number = mask_phone_number(phone_number)
        # Never log plaintext OTP to stdout/stderr or durable logs.
        self._output(f"[secure-ship][sms][console] otp dispatched to {masked_number} message: {message}")
        return SmsSendResult(ok=True, provider="console", masked_phone_number=masked_number)


class SmsService:
    def __init__(self, provider: SmsProvider) -> None:
        self._provider = provider

    def send_otp(self, phone_number: str, otp_code: str) -> SmsSendResult:
        message = (
            "Your SecureShip verification code is "
            f"{otp_code}. It expires soon and can be used only for this chat session."
        )
        return self._provider.send_sms(phone_number, message)


def mask_phone_number(phone_number: str) -> str:
    digits = "".join(character for character in phone_number if character.isdigit())
    if len(digits) <= 4:
        return "*" * max(len(digits), 1)
    return "*" * (len(digits) - 4) + digits[-4:]
