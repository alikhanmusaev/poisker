from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from django.contrib.auth import get_user_model

from notifications.models import PushDevice
from notifications.payloads import TYPE_SYSTEM, default_start_url
from notifications.services import send_push


class Command(BaseCommand):
    help = "Send a test FCM push to all active devices of a user (DEBUG or --force)."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int)
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow outside DEBUG (still requires Firebase credentials).",
        )
        parser.add_argument("--title", default="Тест Поискер")
        parser.add_argument("--body", default="Проверка push-уведомлений")
        parser.add_argument("--url", default="")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to send test push when DEBUG is false (pass --force).")

        User = get_user_model()
        user = User.objects.filter(pk=options["user_id"]).first()
        if not user:
            raise CommandError(f"User {options['user_id']} not found")

        active = PushDevice.objects.filter(user=user, active=True).count()
        if active == 0:
            self.stdout.write(self.style.WARNING("No active devices for user."))
            return

        result = send_push(
            user,
            title=options["title"],
            body=options["body"],
            url=options["url"] or default_start_url(),
            notification_type=TYPE_SYSTEM,
            entity_id="test",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"sent={result['sent']} failed={result['failed']} skipped={result['skipped']}"
            )
        )
