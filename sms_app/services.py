"""
Twilio SMS sending helpers.

Never return raw auth tokens or account secrets in error messages.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass
class SendResult:
    success: bool
    status: str
    sid: str = ""
    error_detail: str = ""
    user_message: str = ""


def twilio_configured() -> bool:
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_PHONE_NUMBER
        and not settings.TWILIO_ACCOUNT_SID.startswith("your_")
        and settings.TWILIO_AUTH_TOKEN != "your_auth_token"
    )


def _safe_twilio_error(exc: Exception) -> str:
    """Sanitize provider errors so secrets never appear in stored/user-facing text."""
    message = str(exc)
    token = settings.TWILIO_AUTH_TOKEN
    sid = settings.TWILIO_ACCOUNT_SID
    if token:
        message = message.replace(token, "[REDACTED]")
    if sid:
        message = message.replace(sid, "[REDACTED]")
    # Truncate overly long provider dumps
    if len(message) > 500:
        message = message[:497] + "..."
    return message


def send_sms(to_number: str, body: str) -> SendResult:
    """
    Send an SMS via Twilio, or simulate in DEMO_MODE.

    Behavior:
    - DEMO_MODE=true → simulate queued success (no API call), record as demo.
    - Credentials missing → friendly configuration error (no API call).
    - Credentials present → real Twilio Messages API create().
    """
    if settings.DEMO_MODE:
        return SendResult(
            success=True,
            status="demo",
            sid="DEMO_SID",
            user_message=(
                "DEMO MODE: message was validated and recorded as queued. "
                "No SMS was sent via Twilio."
            ),
        )

    if not twilio_configured():
        return SendResult(
            success=False,
            status="failed",
            error_detail="Twilio credentials are not configured.",
            user_message=(
                "Twilio is not configured. Copy .env.example to .env and set "
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER. "
                "Or set DEMO_MODE=true for a local demo without Twilio."
            ),
        )

    try:
        from twilio.base.exceptions import TwilioException
        from twilio.rest import Client
    except ImportError:
        return SendResult(
            success=False,
            status="failed",
            error_detail="Twilio SDK is not installed.",
            user_message=(
                "The Twilio library is missing. Run: pip install -r requirements.txt"
            ),
        )

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        sid = getattr(message, "sid", "") or ""
        return SendResult(
            success=True,
            status="queued",
            sid=sid,
            user_message=(
                "SMS submitted to Twilio and queued for delivery. "
                "Submission does not guarantee the recipient has received it yet."
            ),
        )
    except TwilioException as exc:
        detail = _safe_twilio_error(exc)
        return SendResult(
            success=False,
            status="failed",
            error_detail=detail,
            user_message=(
                "Twilio rejected or could not process the request. "
                "Check the recipient number, your Twilio phone number, and account status."
            ),
        )
    except Exception as exc:  # network / unexpected
        detail = _safe_twilio_error(exc)
        return SendResult(
            success=False,
            status="failed",
            error_detail=detail,
            user_message=(
                "Could not reach Twilio (network or provider error). "
                "Try again in a moment."
            ),
        )
