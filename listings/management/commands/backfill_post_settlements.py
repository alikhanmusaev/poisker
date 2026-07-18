from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from listings.models import Post
from locations.models import Settlement


class Command(BaseCommand):
    help = "Link Post.settlement from legacy Post.city slug (Chechnya region code 12 first)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print how many posts would be updated.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        by_slug = {}
        for s in Settlement.objects.filter(is_active=True).select_related("region"):
            key = s.slug
            existing = by_slug.get(key)
            if existing is None:
                by_slug[key] = s
            elif s.region.code == "12" and existing.region.code != "12":
                by_slug[key] = s

        qs = Post.objects.filter(settlement__isnull=True).exclude(city="")
        total = qs.count()
        updated = 0
        unmatched = 0
        batch = []
        for post in qs.iterator(chunk_size=500):
            settlement = by_slug.get(post.city)
            if settlement is None:
                unmatched += 1
                continue
            post.settlement_id = settlement.id
            batch.append(post)
            if len(batch) >= 500:
                if not dry:
                    Post.objects.bulk_update(batch, ["settlement_id"])
                updated += len(batch)
                batch = []
        if batch:
            if not dry:
                Post.objects.bulk_update(batch, ["settlement_id"])
            updated += len(batch)

        if dry:
            transaction.set_rollback(True)

        remaining = (
            Post.objects.filter(settlement__isnull=True).exclude(city="").count()
            if not dry
            else unmatched
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"scanned={total} linked={updated} unmatched={unmatched} "
                f"remaining_null={remaining}"
            )
        )
        if not dry and unmatched:
            top = (
                Post.objects.filter(settlement__isnull=True)
                .exclude(city="")
                .values("city")
                .annotate(c=Count("id"))
                .order_by("-c")[:20]
            )
            for row in top:
                self.stdout.write(f"  unmatched city={row['city']}: {row['c']}")
