from __future__ import annotations

import unittest

from app.services.sms import ConsoleSmsProvider, SmsService, mask_phone_number


class SmsServiceTests(unittest.TestCase):
    def test_mask_phone_number_keeps_last_four_digits(self) -> None:
        masked = mask_phone_number("+1 (415) 555-0112")

        self.assertTrue(masked.endswith("0112"))
        self.assertNotIn("415555", masked)

    def test_console_sms_provider_does_not_log_plaintext_otp(self) -> None:
        output_lines: list[str] = []
        provider = ConsoleSmsProvider(output=output_lines.append)
        service = SmsService(provider)

        result = service.send_otp("+1 (415) 555-0112", "123456")

        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "console")
        self.assertEqual(len(output_lines), 1)
        self.assertNotIn("123456", output_lines[0])
        self.assertIn("0112", output_lines[0])
