from django.core.management.base import BaseCommand
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a production SMTP test message."

    def add_arguments(self, parser):
        parser.add_argument("recipient")

    def handle(self, *args, **options):
        sent = send_mail(
            "Poisker: проверка уведомлений",
            "Почтовые уведомления production настроены.",
            None,
            [options["recipient"]],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"sent={sent}"))
