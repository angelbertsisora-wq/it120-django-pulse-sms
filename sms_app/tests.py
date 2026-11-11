from django.test import Client, TestCase, override_settings

from .forms import SMSForm
from .models import SMSMessage


class SMSFormTests(TestCase):
    def test_valid_e164(self):
        form = SMSForm({"phone_number": "+639171234567", "message": "Hello"})
        self.assertTrue(form.is_valid())

    def test_empty_phone(self):
        form = SMSForm({"phone_number": "", "message": "Hello"})
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_empty_message(self):
        form = SMSForm({"phone_number": "+639171234567", "message": "   "})
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_invalid_phone_format(self):
        form = SMSForm({"phone_number": "09171234567", "message": "Hello"})
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)


@override_settings(
    DEMO_MODE=True,
    TWILIO_ACCOUNT_SID="",
    TWILIO_AUTH_TOKEN="",
    TWILIO_PHONE_NUMBER="",
)
class SendViewDemoTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_ok(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_demo_send_creates_history(self):
        response = self.client.post(
            "/",
            {"phone_number": "+639171234567", "message": "Demo SMS"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SMSMessage.objects.count(), 1)
        row = SMSMessage.objects.get()
        self.assertEqual(row.status, SMSMessage.Status.DEMO)
        self.assertContains(response, "DEMO MODE")


@override_settings(
    DEMO_MODE=False,
    TWILIO_ACCOUNT_SID="",
    TWILIO_AUTH_TOKEN="",
    TWILIO_PHONE_NUMBER="",
)
class MissingCredentialsTests(TestCase):
    def test_missing_credentials_safe_error(self):
        client = Client()
        response = client.post(
            "/",
            {"phone_number": "+639171234567", "message": "Need config"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SMSMessage.objects.count(), 1)
        self.assertEqual(SMSMessage.objects.get().status, SMSMessage.Status.FAILED)
        self.assertContains(response, "not configured")
        self.assertNotContains(response, "AUTH_TOKEN=")
