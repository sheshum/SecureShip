from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


SAFE_NO_MATCH_PAYLOAD = {
    "ok": False,
    "error": "identity_no_match",
    "message": "We could not verify your identity. Please check your details and try again.",
}


@dataclass(frozen=True)
class IdentityMatch:
    customer_id: str


@dataclass(frozen=True)
class IdentityVerificationResult:
    matched: bool
    match: IdentityMatch | None
    error_payload: dict | None = None


class CustomerIdentityLookup(Protocol):
    def list_customers_by_name(self, first_name: str, last_name: str) -> list[dict]: ...


class IdentityVerificationService:
    def __init__(self, customer_lookup: CustomerIdentityLookup) -> None:
        self._customer_lookup = customer_lookup

    def verify_identity(
        self,
        *,
        first_name: str,
        last_name: str,
        phone_number: str,
    ) -> IdentityVerificationResult:
        normalized_first_name = normalize_name(first_name)
        normalized_last_name = normalize_name(last_name)
        normalized_phone_number = normalize_phone_number(phone_number)
        if not normalized_first_name or not normalized_last_name or not normalized_phone_number:
            return IdentityVerificationResult(
                matched=False,
                match=None,
                error_payload=SAFE_NO_MATCH_PAYLOAD,
            )

        candidates = self._customer_lookup.list_customers_by_name(
            normalized_first_name,
            normalized_last_name,
        )

        matches = [
            candidate
            for candidate in candidates
            if normalize_phone_number(str(candidate.get("phone_number", "")))
            == normalized_phone_number
        ]

        if len(matches) != 1:
            return IdentityVerificationResult(
                matched=False,
                match=None,
                error_payload=SAFE_NO_MATCH_PAYLOAD,
            )

        return IdentityVerificationResult(
            matched=True,
            match=IdentityMatch(customer_id=str(matches[0]["id"])),
            error_payload=None,
        )


def normalize_name(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def normalize_phone_number(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"
