from django.conf import settings

from .services import twilio_configured


def twilio_status(request):
    """Expose non-secret Twilio/demo status flags to all templates."""
    return {
        "twilio_is_configured": twilio_configured(),
        "demo_mode_enabled": settings.DEMO_MODE,
    }
