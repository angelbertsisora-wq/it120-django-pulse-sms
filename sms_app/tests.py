from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings

from .forms import SMSForm
from .models import SMSMessage
from .services import refresh_queued_statuses, send_sms


class SMSFormTests(TestCase):
    def test_valid_phone_and_message(self):
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

    def test_invalid_e164_too_short(self):
        form = SMSForm({"phone_number": "+123", "message": "Hello"})
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)


@override_settings(
    DEMO_MODE=True,
    TEXTBEE_API_KEY="",
    TEXTBEE_DEVICE_ID="",
)
class DemoModeTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_ok(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demo (optional")

    def test_demo_send_creates_history(self):
        response = self.client.post(
            "/",
            {"phone_number": "+639171234567", "message": "Demo SMS"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        row = SMSMessage.objects.get()
        self.assertEqual(row.status, SMSMessage.Status.DEMO)
        self.assertTrue(row.is_demo)
        self.assertEqual(row.twilio_sid, "DEMO_SID")
        self.assertContains(response, "Demo mode")

    @patch("sms_app.services.requests.post")
    def test_demo_mode_never_calls_textbee(self, mock_post):
        result = send_sms("+639171234567", "No API")
        self.assertTrue(result.is_demo)
        self.assertEqual(result.status, SMSMessage.Status.DEMO)
        mock_post.assert_not_called()


@override_settings(
    DEMO_MODE=False,
    TEXTBEE_API_KEY="",
    TEXTBEE_DEVICE_ID="",
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
        row = SMSMessage.objects.get()
        self.assertEqual(row.status, SMSMessage.Status.FAILED)
        self.assertFalse(row.is_demo)
        self.assertContains(response, "TEXTBEE_API_KEY")
        self.assertNotContains(response, "txb_")
        self.assertNotContains(response, "DEMO_SID")


@override_settings(
    DEMO_MODE=False,
    TEXTBEE_BASE_URL="https://api.textbee.dev/api/v1",
    TEXTBEE_API_KEY="txb_test_key_not_real",
    TEXTBEE_DEVICE_ID="device_test_1",
)
class LiveTextBeeMockTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _ok_response(self, batch_id="batch-textbee-1"):
        response = MagicMock()
        response.status_code = 200
        response.text = "{}"
        response.json.return_value = {
            "data": {
                "success": True,
                "message": "SMS added to queue for processing",
                "smsBatchId": batch_id,
                "recipientCount": 1,
            }
        }
        return response

    @patch("sms_app.services.requests.post")
    def test_actual_api_success_queued(self, mock_post):
        mock_post.return_value = self._ok_response()
        response = self.client.post(
            "/",
            {"phone_number": "+639171234567", "message": "Live mock"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        row = SMSMessage.objects.get()
        self.assertEqual(row.status, SMSMessage.Status.QUEUED)
        self.assertFalse(row.is_demo)
        self.assertEqual(row.twilio_sid, "batch-textbee-1")
        self.assertContains(response, "queued")
        self.assertContains(response, "batch-textbee-1")
        self.assertNotContains(response, "SMS delivered")

        # Ensure deviceId is forwarded
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["deviceId"], "device_test_1")
        self.assertEqual(kwargs["headers"]["x-api-key"], "txb_test_key_not_real")

    @patch("sms_app.services.requests.post")
    def test_invalid_textbee_credentials(self, mock_post):
        response = MagicMock()
        response.status_code = 401
        response.text = '{"error":"Unauthorized","code":"AUTH_INVALID"}'
        mock_post.return_value = response

        result_response = self.client.post(
            "/",
            {"phone_number": "+639171234567", "message": "Bad creds"},
            follow=True,
        )
        row = SMSMessage.objects.get()
        self.assertEqual(row.status, SMSMessage.Status.FAILED)
        self.assertFalse(row.is_demo)
        self.assertContains(result_response, "API key")
        self.assertNotContains(result_response, "txb_test_key_not_real")

    @patch("sms_app.services.requests.post")
    def test_textbee_api_failure(self, mock_post):
        response = MagicMock()
        response.status_code = 400
        response.text = "No enabled device to send from"
        mock_post.return_value = response

        result = send_sms("+639171234567", "No device")
        self.assertFalse(result.success)
        self.assertEqual(result.status, SMSMessage.Status.FAILED)
        self.assertIn("device", result.user_message.lower())

    @patch("sms_app.services.requests.post")
    def test_network_connection_failure(self, mock_post):
        mock_post.side_effect = __import__("requests").exceptions.ConnectionError(
            "Network unreachable"
        )
        result = send_sms("+639171234567", "Offline")
        self.assertFalse(result.success)
        self.assertEqual(result.status, SMSMessage.Status.FAILED)
        self.assertIn("network", result.user_message.lower())
        self.assertFalse(result.is_demo)

    @patch("sms_app.services.requests.post")
    def test_history_records_live_attempt(self, mock_post):
        mock_post.return_value = self._ok_response("batch-history-1")
        self.client.post(
            "/",
            {"phone_number": "+639171234567", "message": "History check"},
            follow=True,
        )
        row = SMSMessage.objects.get()
        self.assertEqual(row.to_number, "+639171234567")
        self.assertEqual(row.body, "History check")
        self.assertEqual(row.twilio_sid, "batch-history-1")
        self.assertFalse(row.is_demo)
        self.assertEqual(row.error_detail, "")

    @patch("sms_app.services.requests.get")
    def test_refresh_updates_queued_to_sent(self, mock_get):
        SMSMessage.objects.create(
            to_number="+639356818783",
            body="hi",
            status=SMSMessage.Status.QUEUED,
            twilio_sid="batch-refresh-1",
            is_demo=False,
        )
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "smsBatch": "batch-refresh-1",
                    "status": "sent",
                    "recipient": "+639356818783",
                    "message": "hi",
                }
            ]
        }
        mock_get.return_value = response

        updated = refresh_queued_statuses()
        self.assertEqual(updated, 1)
        row = SMSMessage.objects.get(twilio_sid="batch-refresh-1")
        self.assertEqual(row.status, SMSMessage.Status.SENT)


class CsrfProtectionTests(TestCase):
    @override_settings(DEMO_MODE=True)
    def test_post_without_csrf_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/")
        response = client.post(
            "/",
            {"phone_number": "+639171234567", "message": "No CSRF"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(SMSMessage.objects.count(), 0)
