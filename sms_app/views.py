from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_http_methods

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
    # Compact preview on the send page; full list lives on History.
    history = SMSMessage.objects.all()[:5]
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


@require_GET
def history_refresh_api(request):
    """
    Sync queued TextBee statuses and return updated history HTML for auto-refresh.
    """
    limit = 25
    raw_limit = request.GET.get("limit", "25")
    try:
        limit = max(1, min(100, int(raw_limit)))
    except (TypeError, ValueError):
        limit = 25

    updated = refresh_queued_statuses(limit=limit)
    history = list(SMSMessage.objects.all()[:limit])
    queued_count = sum(1 for row in history if row.status == SMSMessage.Status.QUEUED and not row.is_demo)
    html = render_to_string(
        "sms_app/_history_table.html",
        {
            "history": history,
            "empty_message": request.GET.get(
                "empty",
                "No messages yet. Send your first SMS to see it here.",
            ),
        },
        request=request,
    )
    return JsonResponse(
        {
            "updated": updated,
            "queued_count": queued_count,
            "html": html,
        }
    )
