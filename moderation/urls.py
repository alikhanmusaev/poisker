from django.urls import path

from moderation import views

app_name = "moderation"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("queue/", views.queue, name="queue"),
    path("reports/", views.reports, name="reports"),
    path("posts/<uuid:post_id>/", views.post_detail, name="post_detail"),
    path("posts/<uuid:post_id>/approve/", views.approve, name="approve"),
    path("posts/<uuid:post_id>/reject/", views.reject, name="reject"),
    path("posts/<uuid:post_id>/hide/", views.hide, name="hide"),
    path("posts/<uuid:post_id>/resolve-reports/", views.post_resolve_reports, name="resolve_reports"),
    path("reports/<int:report_id>/review/", views.report_review, name="report_review"),
]
