from django.conf import settings

from .services import provider_configured


def provider_status(request):
    """Expose non-secret mode flags to all templates (never credentials)."""
    configured = provider_configured()
    demo = bool(settings.DEMO_MODE)
    if demo:
        mode_label = "Demo mode"
    elif configured:
        mode_label = "Actual TextBee mode"
    else:
        mode_label = "Actual mode (credentials missing)"
    return {
        "twilio_is_configured": configured,  # legacy template alias
        "provider_is_configured": configured,
        "demo_mode_enabled": demo,
        "app_mode_label": mode_label,
        "sms_provider_name": "TextBee",
    }
