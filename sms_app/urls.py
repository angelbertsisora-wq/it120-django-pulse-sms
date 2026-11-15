from django.urls import path

from . import views

app_name = "sms_app"

urlpatterns = [
    path("", views.send_sms_view, name="send"),
    path("history/", views.history_view, name="history"),
    path("api/history-refresh/", views.history_refresh_api, name="history_refresh"),
]
