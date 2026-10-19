import unittest
from app.main import OTP_TTL_SECONDS, body_hash, fingerprint, mask_email


class PaymentDomainTests(unittest.TestCase):
    def test_otp_ttl_never_exceeds_five_minutes(self):
        self.assertLessEqual(OTP_TTL_SECONDS, 300)

    def test_otp_fingerprint_is_deterministic_and_not_plaintext(self):
        value = fingerprint("123456")
        self.assertEqual(value, fingerprint("123456"))
        self.assertNotIn("123456", value)

    def test_request_hash_is_canonical(self):
        self.assertEqual(body_hash({"a": 1, "b": 2}), body_hash({"b": 2, "a": 1}))

    def test_email_is_masked(self):
        self.assertEqual(mask_email("payer@example.com"), "pa***@example.com")


if __name__ == "__main__":
    unittest.main()
