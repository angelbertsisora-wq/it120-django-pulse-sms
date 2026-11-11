from django.db import models
from django.utils import timezone


class SMSMessage(models.Model):
    """Persists each SMS send attempt for history and debugging."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued / Submitted"
        FAILED = "failed", "Failed"
        DEMO = "demo", "Demo (simulated)"

    to_number = models.CharField(max_length=20)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    twilio_sid = models.CharField(max_length=64, blank=True, default="")
    error_detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS message"
        verbose_name_plural = "SMS messages"

    def __str__(self):
        return f"{self.to_number} [{self.status}] @ {self.created_at:%Y-%m-%d %H:%M}"
