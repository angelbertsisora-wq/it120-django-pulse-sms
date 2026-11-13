from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SMSForm
from .models import SMSMessage
from .services import refresh_queued_statuses, send_sms


@require_http_methods(["GET", "POST"])
def send_sms_view(request):
    form = SMSForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            phone = form.cleaned_data["phone_number"]
            body = form.cleaned_data["message"]
            result = send_sms(phone, body)

            SMSMessage.objects.create(
                to_number=phone,
                body=body,
                status=result.status,
                twilio_sid=result.sid,
                error_detail=result.error_detail,
                is_demo=result.is_demo,
            )

            if result.success:
                messages.success(request, result.user_message)
            else:
                messages.error(request, result.user_message)

            return redirect("sms_app:send")
        messages.error(request, "Please fix the errors below and try again.")

    # Pull later TextBee results (sent/failed/delivered) into local history.
    refresh_queued_statuses()
    history = SMSMessage.objects.all()[:25]
    return render(
        request,
        "sms_app/send.html",
        {
            "form": form,
            "history": history,
        },
    )


@require_http_methods(["GET"])
def history_view(request):
    refresh_queued_statuses(limit=100)
    history = SMSMessage.objects.all()[:100]
    return render(request, "sms_app/history.html", {"history": history})
