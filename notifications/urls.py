from django.urls import path

from notifications import views

app_name = "notifications"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("unregister/", views.unregister, name="unregister"),
]
