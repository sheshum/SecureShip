from __future__ import annotations

import unittest
from uuid import uuid4

from app.services.identity_verification import (
    IdentityVerificationService,
    SAFE_NO_MATCH_PAYLOAD,
    normalize_name,
    normalize_phone_number,
)


class FakeCustomerLookup:
    def __init__(self, customers: list[dict]) -> None:
        self._customers = customers

    def list_customers_by_name(self, first_name: str, last_name: str) -> list[dict]:
        return [
            customer
            for customer in self._customers
            if normalize_name(customer["first_name"]) == first_name
            and normalize_name(customer["last_name"]) == last_name
        ]


class IdentityNormalizationTests(unittest.TestCase):
    def test_normalize_name_collapses_whitespace_and_case(self) -> None:
        self.assertEqual(normalize_name("  MARy   Ann "), "mary ann")

    def test_normalize_phone_number_strips_formatting(self) -> None:
        self.assertEqual(normalize_phone_number("(415) 555-0112"), "+14155550112")
        self.assertEqual(normalize_phone_number("+1 415 555 0112"), "+14155550112")


class IdentityVerificationServiceTests(unittest.TestCase):
    def test_verify_identity_returns_match_for_known_fixture(self) -> None:
        customer_id = uuid4()
        service = IdentityVerificationService(
            FakeCustomerLookup(
                [
                    {
                        "id": str(customer_id),
                        "first_name": "Mary",
                        "last_name": "Johnson",
                        "phone_number": "+1 (415) 555-0112",
                    }
                ]
            )
        )

        result = service.verify_identity(
            first_name=" mary ",
            last_name="JOHNSON",
            phone_number="415-555-0112",
        )

        self.assertTrue(result.matched)
        self.assertIsNotNone(result.match)
        self.assertEqual(result.match.customer_id, str(customer_id))
        self.assertIsNone(result.error_payload)

    def test_verify_identity_returns_safe_payload_for_no_match(self) -> None:
        service = IdentityVerificationService(
            FakeCustomerLookup(
                [
                    {
                        "id": str(uuid4()),
                        "first_name": "Mary",
                        "last_name": "Johnson",
                        "phone_number": "+14155550112",
                    }
                ]
            )
        )

        result = service.verify_identity(
            first_name="Mary",
            last_name="Johnson",
            phone_number="+14155559999",
        )

        self.assertFalse(result.matched)
        self.assertIsNone(result.match)
        self.assertEqual(result.error_payload, SAFE_NO_MATCH_PAYLOAD)

    def test_verify_identity_returns_safe_payload_when_multiple_customers_match(self) -> None:
        service = IdentityVerificationService(
            FakeCustomerLookup(
                [
                    {
                        "id": str(uuid4()),
                        "first_name": "Mary",
                        "last_name": "Johnson",
                        "phone_number": "+14155550112",
                    },
                    {
                        "id": str(uuid4()),
                        "first_name": "Mary",
                        "last_name": "Johnson",
                        "phone_number": "+14155550112",
                    },
                ]
            )
        )

        result = service.verify_identity(
            first_name="Mary",
            last_name="Johnson",
            phone_number="+14155550112",
        )

        self.assertFalse(result.matched)
        self.assertIsNone(result.match)
        self.assertEqual(result.error_payload, SAFE_NO_MATCH_PAYLOAD)
