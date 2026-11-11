import re

from django import forms


# E.164: + followed by 8–15 digits (country code + subscriber number)
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class SMSForm(forms.Form):
    phone_number = forms.CharField(
        label="Recipient phone number",
        max_length=20,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+639171234567",
                "autocomplete": "tel",
                "inputmode": "tel",
            }
        ),
        help_text="Use E.164 format, e.g. +639171234567 (include country code).",
    )
    message = forms.CharField(
        label="Message",
        required=True,
        max_length=1600,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Type your SMS message here…",
                "id": "id_message",
            }
        ),
        help_text="Standard SMS segments are about 160 characters (GSM-7).",
    )

    def clean_phone_number(self):
        value = (self.cleaned_data.get("phone_number") or "").strip().replace(" ", "")
        if not value:
            raise forms.ValidationError("Phone number is required.")
        if not E164_PATTERN.match(value):
            raise forms.ValidationError(
                "Enter a valid E.164 phone number (e.g. +639171234567)."
            )
        return value

    def clean_message(self):
        value = (self.cleaned_data.get("message") or "").strip()
        if not value:
            raise forms.ValidationError("Message is required.")
        return value
