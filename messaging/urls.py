from django.urls import path

from messaging import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("report/<int:message_id>/", views.report_message, name="report_message"),
    path("<uuid:conversation_id>/confirm-deal/", views.confirm_deal, name="confirm_deal"),
    path("<uuid:conversation_id>/block/", views.block_user, name="block_user"),
    path("<uuid:conversation_id>/unblock/", views.unblock_user, name="unblock_user"),
    path("<uuid:conversation_id>/delete/", views.delete_conversation, name="delete"),
    path("<uuid:conversation_id>/", views.thread, name="thread"),
    path("start/<uuid:post_id>/", views.start, name="start"),
]
