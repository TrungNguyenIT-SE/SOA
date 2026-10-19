import unittest
from unittest.mock import MagicMock, patch

from app import worker
from app.worker import render, render_html


class NotificationTemplateTests(unittest.TestCase):
    def test_otp_template_contains_transaction_context(self):
        _, subject, content = render({"type":"otp.requested","to":"a@b.test","payer_name":"A","student_code":"52400001","otp":"123456","amount":1200000,"payment_id":"p1","expires_at":"now"})
        self.assertIn("52400001", subject)
        self.assertIn("[iBanking Tuition]", subject)
        self.assertIn("p1", content)
        self.assertIn("123456", content)
        self.assertIn("vừa yêu cầu thanh toán", content)

    def test_completion_template_contains_balance(self):
        _, _, content = render({"type":"payment.completed","to":"a@b.test","payer_name":"A","student_name":"B","student_code":"52400001","amount":1200000,"balance_after":3800000,"payment_id":"p1","completed_at":"now"})
        self.assertIn("3.800.000 VND", content)

    def test_otp_html_matches_website_brand_and_escapes_values(self):
        html = render_html({"type":"otp.requested","to":"a@b.test","payer_name":"<Khoa>","student_code":"52400001","otp":"123456","amount":1200000,"payment_id":"p1","expires_at":"2026-10-20T01:00:00+00:00"})
        self.assertIn("iBanking", html)
        self.assertIn("#0b1731", html)
        self.assertIn("123456", html)
        self.assertIn("&lt;Khoa&gt;", html)
        self.assertNotIn("<Khoa>", html)

    def test_completion_html_is_a_receipt(self):
        html = render_html({"type":"payment.completed","to":"a@b.test","payer_name":"A","student_name":"B","student_code":"52400001","amount":1200000,"balance_after":3800000,"payment_id":"p1","completed_at":"2026-10-20T01:00:00+00:00"})
        self.assertIn("biên nhận điện tử", html)
        self.assertIn("3.800.000 VND", html)

    @patch.object(worker.smtplib, "SMTP")
    def test_real_smtp_uses_starttls_authentication(self, smtp_class):
        smtp = MagicMock()
        smtp_class.return_value.__enter__.return_value = smtp
        with (
            patch.object(worker, "SMTP_HOST", "smtp.example.com"),
            patch.object(worker, "SMTP_PORT", 587),
            patch.object(worker, "SMTP_USERNAME", "sender@example.com"),
            patch.object(worker, "SMTP_PASSWORD", "app-password"),
            patch.object(worker, "SMTP_USE_TLS", True),
            patch.object(worker, "SMTP_USE_SSL", False),
            patch.object(worker, "FROM_EMAIL", "sender@example.com"),
        ):
            worker.send_email("recipient@example.com", "OTP", "123456", "<strong>123456</strong>")

        smtp_class.assert_called_once()
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("sender@example.com", "app-password")
        smtp.send_message.assert_called_once()
        message = smtp.send_message.call_args.args[0]
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_body(preferencelist=("html",)).get_content_type(), "text/html")
        self.assertIn("iBanking Tuition", str(message["From"]))
        self.assertTrue(message["Date"])
        self.assertTrue(message["Message-ID"])
        self.assertEqual(message["Auto-Submitted"], "auto-generated")

    def test_real_smtp_configuration_is_required(self):
        with (
            patch.object(worker, "SMTP_HOST", ""),
            patch.object(worker, "SMTP_USERNAME", ""),
            patch.object(worker, "SMTP_PASSWORD", ""),
            patch.object(worker, "FROM_EMAIL", ""),
        ):
            with self.assertRaisesRegex(RuntimeError, "SMTP_HOST"):
                worker.validate_smtp_config()


if __name__ == "__main__":
    unittest.main()
