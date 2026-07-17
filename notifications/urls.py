from django.urls import path

from notifications.views import (
    NotificationPreferenceView,
    PushDeviceCurrentView,
    PushDeviceRegisterView,
)

app_name = "notifications"

urlpatterns = [
    path("devices/", PushDeviceRegisterView.as_view(), name="device-register"),
    path("devices/current/", PushDeviceCurrentView.as_view(), name="device-current"),
    path("preferences/", NotificationPreferenceView.as_view(), name="preferences"),
]
