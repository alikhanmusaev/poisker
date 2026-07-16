import os

from django.core.management.base import BaseCommand

from listings.services.search import ensure_collection, reindex_published_posts
from listings.services.storage import ensure_bucket


class Command(BaseCommand):
    help = "Initialize storage bucket and search index"

    def handle(self, *args, **options):
        try:
            ensure_bucket()
            self.stdout.write(self.style.SUCCESS("Storage bucket ready"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Storage bucket skipped: {exc}"))
        try:
            ensure_collection()
            self.stdout.write(self.style.SUCCESS("Typesense collection ready"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Typesense skipped: {exc}"))

        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                display_name=os.getenv("ADMIN_USERNAME", "admin"),
                phone=os.getenv("ADMIN_PHONE", "+79000000001"),
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {admin_email}"))

        try:
            count = reindex_published_posts()
            self.stdout.write(self.style.SUCCESS(f"Indexed {count} published posts"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Reindex skipped: {exc}"))
