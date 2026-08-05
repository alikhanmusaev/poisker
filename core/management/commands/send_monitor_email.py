from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send a production monitoring alert."

    def add_arguments(self, parser):
        parser.add_argument("recipient")
        parser.add_argument("subject")
        parser.add_argument("body")

    def handle(self, *args, **options):
        send_mail(options["subject"], options["body"], None, [options["recipient"]], fail_silently=False)
