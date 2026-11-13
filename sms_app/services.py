"""
TextBee SMS sending helpers.

Never return raw API keys or secrets in error messages.
Never silently fall back to demo mode when a live send fails.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

from .models import SMSMessage


@dataclass
class SendResult:
    success: bool
    status: str
    sid: str = ""
    error_detail: str = ""
    user_message: str = ""
    is_demo: bool = False


def provider_configured() -> bool:
    """Return True when a non-placeholder TextBee API key is present."""
    key = (settings.TEXTBEE_API_KEY or "").strip()
    if not key:
        return False
    if key.lower().startswith("your_"):
        return False
    return True


def twilio_configured() -> bool:
    """Backward-compatible alias."""
    return provider_configured()


def _normalize_base_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        value = "https://api.textbee.dev/api/v1"
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value


def _safe_text(text: str) -> str:
    message = text or ""
    key = settings.TEXTBEE_API_KEY or ""
    if key:
        message = message.replace(key, "[REDACTED]")
    if len(message) > 500:
        message = message[:497] + "..."
    return message


def _classify_http_error(status_code: int, body_text: str) -> tuple[str, str]:
    detail = _safe_text(body_text)
    lowered = detail.lower()
    if status_code == 401:
        return (
            detail,
            "TextBee rejected the API key. Check TEXTBEE_API_KEY in your .env file.",
        )
    if status_code == 404:
        return (
            detail,
            "TextBee device was not found. Check TEXTBEE_DEVICE_ID in your .env file.",
        )
    if status_code == 400:
        if "device" in lowered or "enabled" in lowered:
            return (
                detail,
                "TextBee has no enabled/online device to send from. Open the TextBee "
                "Android app, keep the phone online, and confirm the device is enabled.",
            )
        if "email" in lowered and "verif" in lowered:
            return (
                detail,
                "Verify your email in the TextBee dashboard, then try again.",
            )
        return (
            detail,
            "TextBee rejected the request (invalid recipient, device, or payload). "
            "Use E.164 numbers like +639171234567.",
        )
    if status_code == 429:
        return (
            detail,
            "TextBee plan limit reached (daily/monthly/batch). Wait or upgrade your plan.",
        )
    if status_code >= 500:
        return (
            detail,
            "TextBee is temporarily unavailable. Try again in a moment.",
        )
    return (
        detail,
        "TextBee could not process the SMS request. Check device status and account limits.",
    )


def send_sms(to_number: str, body: str) -> SendResult:
    """
    Send an SMS via TextBee, or simulate only when DEMO_MODE is explicitly enabled.

    Behavior:
    - DEMO_MODE=true → simulate only (no API call); status=demo, is_demo=True.
    - DEMO_MODE=false + API key missing → configuration error (failed), never demo.
    - DEMO_MODE=false + API key present → real TextBee gateway send-sms API.
    - Live API failures stay failed; there is no silent demo fallback.
    """
    if settings.DEMO_MODE:
        return SendResult(
            success=True,
            status=SMSMessage.Status.DEMO,
            sid="DEMO_SID",
            is_demo=True,
            user_message=(
                "Demo mode: message validated and recorded as a simulation. "
                "TextBee was not called, and no real SMS was submitted."
            ),
        )

    if not provider_configured():
        return SendResult(
            success=False,
            status=SMSMessage.Status.FAILED,
            is_demo=False,
            error_detail="TextBee credentials are not configured.",
            user_message=(
                "Actual TextBee mode is enabled, but TEXTBEE_API_KEY is missing or still "
                "a placeholder. Set it in .env (and optionally TEXTBEE_DEVICE_ID). "
                "For a local simulation only, set DEMO_MODE=true."
            ),
        )

    base = _normalize_base_url(settings.TEXTBEE_BASE_URL)
    url = f"{base}/gateway/send-sms"
    headers = {
        "x-api-key": settings.TEXTBEE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "recipients": [to_number],
        "message": body,
    }
    device_id = (settings.TEXTBEE_DEVICE_ID or "").strip()
    if device_id and not device_id.lower().startswith("your_"):
        payload["deviceId"] = device_id

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.exceptions.RequestException as exc:
        return SendResult(
            success=False,
            status=SMSMessage.Status.FAILED,
            is_demo=False,
            error_detail=_safe_text(str(exc)),
            user_message=(
                "Could not reach TextBee due to a network error. "
                "Check your internet connection and try again."
            ),
        )

    body_text = response.text or ""
    if response.status_code >= 400:
        detail, user_message = _classify_http_error(response.status_code, body_text)
        return SendResult(
            success=False,
            status=SMSMessage.Status.FAILED,
            is_demo=False,
            error_detail=detail,
            user_message=user_message,
        )

    try:
        data = response.json()
    except ValueError:
        return SendResult(
            success=False,
            status=SMSMessage.Status.FAILED,
            is_demo=False,
            error_detail=_safe_text(body_text or "Invalid JSON from TextBee"),
            user_message="TextBee returned an unexpected response. Try again in a moment.",
        )

    # Response shape: { "data": { "success": true, "smsBatchId": "...", ... } }
    payload_data = data.get("data") if isinstance(data, dict) else None
    if not isinstance(payload_data, dict):
        payload_data = data if isinstance(data, dict) else {}

    batch_id = str(payload_data.get("smsBatchId") or "")
    api_success = bool(payload_data.get("success", True))
    api_message = str(payload_data.get("message") or "")

    if not api_success:
        return SendResult(
            success=False,
            status=SMSMessage.Status.FAILED,
            sid=batch_id,
            is_demo=False,
            error_detail=_safe_text(api_message or body_text),
            user_message=(
                "TextBee did not accept the message. Check your device is online "
                "and the recipient number is valid."
            ),
        )

    # 200 + success means accepted/queued for the Android gateway — not delivered.
    user_message = (
        f"SMS submitted to TextBee and queued for your device (ID: {batch_id}). "
        "History will refresh to Sent/Failed when TextBee reports the phone result. "
        "Keep the TextBee Android app online so the phone can send via SIM."
        if batch_id
        else (
            "SMS submitted to TextBee and queued for your device. "
            "History will refresh to Sent/Failed when TextBee reports the phone result. "
            "Keep the TextBee Android app online so the phone can send via SIM."
        )
    )

    return SendResult(
        success=True,
        status=SMSMessage.Status.QUEUED,
        sid=batch_id,
        is_demo=False,
        user_message=user_message,
    )


def _map_textbee_history_status(raw_status: str | None) -> str | None:
    """Map TextBee message history status to our model status."""
    value = (raw_status or "").strip().lower()
    if value in {"pending", "dispatched"}:
        return SMSMessage.Status.QUEUED
    if value == "sent":
        return SMSMessage.Status.SENT
    if value == "delivered":
        return SMSMessage.Status.DELIVERED
    if value == "failed":
        return SMSMessage.Status.FAILED
    return None


def refresh_queued_statuses(limit: int = 40) -> int:
    """
    Update local Actual-mode rows that are still queued by checking TextBee message history.

    Returns the number of rows updated. Failures are ignored (page still loads).
    """
    if settings.DEMO_MODE or not provider_configured():
        return 0

    pending = list(
        SMSMessage.objects.filter(
            is_demo=False,
            status=SMSMessage.Status.QUEUED,
        )
        .exclude(twilio_sid="")
        .order_by("-created_at")[:limit]
    )
    if not pending:
        return 0

    batch_ids = {row.twilio_sid for row in pending}
    base = _normalize_base_url(settings.TEXTBEE_BASE_URL)
    headers = {
        "x-api-key": settings.TEXTBEE_API_KEY,
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            f"{base}/gateway/messages",
            headers=headers,
            params={"direction": "sent", "limit": 50},
            timeout=20,
        )
    except requests.exceptions.RequestException:
        return 0

    if response.status_code >= 400:
        return 0

    try:
        payload = response.json()
    except ValueError:
        return 0

    messages = payload.get("data") or []
    by_batch: dict[str, dict] = {}
    for item in messages:
        batch = str(item.get("smsBatch") or "")
        if batch and batch in batch_ids and batch not in by_batch:
            by_batch[batch] = item

    updated = 0
    for row in pending:
        item = by_batch.get(row.twilio_sid)
        if not item:
            continue
        mapped = _map_textbee_history_status(item.get("status"))
        if not mapped or mapped == row.status:
            continue

        row.status = mapped
        if mapped == SMSMessage.Status.FAILED:
            err = item.get("errorMessage") or item.get("deviceMessage") or item.get("errorCode") or ""
            row.error_detail = _safe_text(str(err))
        elif mapped in {SMSMessage.Status.SENT, SMSMessage.Status.DELIVERED}:
            row.error_detail = ""
        row.save(update_fields=["status", "error_detail"])
        updated += 1

    return updated

