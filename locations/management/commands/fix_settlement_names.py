"""Apply Russian name/slug overrides to existing Settlement rows."""

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from locations.models import Settlement
from locations.region_names import SETTLEMENT_OVERRIDES_BY_GEONAME


class Command(BaseCommand):
    help = "Fix settlement display names/slugs from SETTLEMENT_OVERRIDES_BY_GEONAME."

    @transaction.atomic
    def handle(self, *args, **options):
        updated = 0
        missing = 0
        for geoname_id, override in SETTLEMENT_OVERRIDES_BY_GEONAME.items():
            settlement = Settlement.objects.filter(geoname_id=geoname_id).first()
            if settlement is None:
                missing += 1
                continue
            fields = []
            name = override.get("name")
            slug = override.get("slug")
            if name and settlement.name != name:
                settlement.name = name
                fields.append("name")
            if slug and settlement.slug != slug:
                # Avoid unique constraint collisions inside the region.
                clash = (
                    Settlement.objects.filter(region_id=settlement.region_id, slug=slug)
                    .exclude(pk=settlement.pk)
                    .exists()
                )
                if clash:
                    slug = f"{slug}-{geoname_id}"
                settlement.slug = slug
                fields.append("slug")
            if fields:
                fields.append("updated_at")
                settlement.save(update_fields=fields)
                updated += 1

        cache.delete_many(
            [f"loc:popular:v1:{n}" for n in range(1, 31)]
            + [f"loc:search:v1:" ]  # no-op prefix; clear popular is enough
        )
        try:
            cache.clear()
        except Exception:
            pass

        self.stdout.write(
            self.style.SUCCESS(f"updated={updated} missing_geoname={missing}")
        )
