from django.db import models
from django.utils import timezone


class SMSMessage(models.Model):
    """Persists each SMS send attempt for history and debugging."""

    class Status(models.TextChoices):
        DEMO = "demo", "Demo (simulated)"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    to_number = models.CharField(max_length=20)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    twilio_sid = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Provider message/batch ID (TextBee smsBatchId / demo SID).",
    )
    error_detail = models.TextField(blank=True, default="")
    is_demo = models.BooleanField(
        default=False,
        help_text="True when the attempt was simulated under DEMO_MODE (no provider API call).",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS message"
        verbose_name_plural = "SMS messages"

    def __str__(self):
        mode = "demo" if self.is_demo else "live"
        return f"{self.to_number} [{self.status}/{mode}] @ {self.created_at:%Y-%m-%d %H:%M}"
