from django.contrib import admin

from .models import SMSMessage


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ("to_number", "status", "is_demo", "twilio_sid", "created_at")
    list_filter = ("status", "is_demo")
    search_fields = ("to_number", "body", "twilio_sid", "error_detail")
    readonly_fields = ("created_at",)
