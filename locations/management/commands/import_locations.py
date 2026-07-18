from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from listings.data.chechnya_settlements import CHECHNYA_SETTLEMENTS
from locations.models import Region, Settlement
from locations.region_names import (
    POPULAR_SETTLEMENT_GEONAMES,
    REGION_RU_NAMES,
    REGION_SLUG_OVERRIDES,
    SETTLEMENT_OVERRIDES_BY_GEONAME,
)
from locations.slugify import slugify_ru

BATCH = 2000


def _dec(value: str):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int(value: str, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except (TypeError, ValueError):
        return default


class Command(BaseCommand):
    help = "Import Russian regions and settlements from CSV (GeoNames export)."

    def add_arguments(self, parser):
        parser.add_argument(
            "settlements_csv",
            nargs="?",
            default="locations/data/settlements.csv",
            help="Path to settlements.csv",
        )
        parser.add_argument(
            "--regions-csv",
            default="locations/data/regions.csv",
            help="Path to regions.csv",
        )
        parser.add_argument(
            "--skip-legacy-chechnya",
            action="store_true",
            help="Do not upsert legacy Chechnya settlement slugs",
        )

    def handle(self, *args, **options):
        settlements_path = Path(options["settlements_csv"])
        regions_path = Path(options["regions_csv"])
        if not settlements_path.exists():
            raise CommandError(f"File not found: {settlements_path}")
        if not regions_path.exists():
            raise CommandError(f"File not found: {regions_path}")

        with transaction.atomic():
            region_stats = self._import_regions(regions_path)
            settlement_stats = self._import_settlements(settlements_path)
            if not options["skip_legacy_chechnya"]:
                legacy_stats = self._upsert_legacy_chechnya()
            else:
                legacy_stats = {"created": 0, "updated": 0}
            popular = self._mark_popular()

        self.stdout.write(
            self.style.SUCCESS(
                "Import complete: "
                f"regions +{region_stats['created']}/~{region_stats['updated']}, "
                f"settlements +{settlement_stats['created']}/~{settlement_stats['updated']}, "
                f"legacy chechnya +{legacy_stats['created']}/~{legacy_stats['updated']}, "
                f"popular={popular}"
            )
        )

    def _import_regions(self, path: Path) -> dict:
        created = updated = skipped = 0
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                code = (row.get("code") or "").strip()
                if not code or code in {"00", "JA"}:
                    skipped += 1
                    continue
                name = REGION_RU_NAMES.get(code) or (row.get("name") or "").strip()
                if not name or name.startswith("Регион "):
                    skipped += 1
                    continue
                slug = REGION_SLUG_OVERRIDES.get(code) or slugify_ru(name)
                geoname_id = _int(row.get("geoname_id") or 0) or None
                obj, was_created = Region.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "slug": slug,
                        "geoname_id": geoname_id,
                        "is_active": True,
                    },
                )
                # Resolve slug collisions on name change
                if Region.objects.filter(slug=obj.slug).exclude(pk=obj.pk).exists():
                    obj.slug = f"{slug}-{code.lower()}"
                    obj.save(update_fields=["slug", "updated_at"])
                if was_created:
                    created += 1
                else:
                    updated += 1
        return {"created": created, "updated": updated, "skipped": skipped}

    def _import_settlements(self, path: Path) -> dict:
        regions = {r.code: r for r in Region.objects.all()}
        existing = {
            s.geoname_id: s
            for s in Settlement.objects.exclude(geoname_id=None).only(
                "id", "geoname_id", "region_id", "name", "slug", "type",
                "latitude", "longitude", "population", "timezone", "is_active",
            )
        }
        to_create: list[Settlement] = []
        to_update: list[Settlement] = []
        created = updated = skipped = 0
        seen_slugs: dict[tuple[int, str], int] = {}

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                code = (row.get("region_code") or "").strip()
                region = regions.get(code)
                if region is None:
                    skipped += 1
                    continue
                geoname_id = _int(row.get("geoname_id") or 0) or None
                if not geoname_id:
                    skipped += 1
                    continue

                override = SETTLEMENT_OVERRIDES_BY_GEONAME.get(geoname_id, {})
                name = override.get("name") or (row.get("name") or "").strip()
                if not name:
                    skipped += 1
                    continue
                slug = override.get("slug") or (row.get("slug") or "").strip() or slugify_ru(name)
                key = (region.id, slug)
                if key in seen_slugs and seen_slugs[key] != geoname_id:
                    slug = f"{slug}-{geoname_id}"
                    key = (region.id, slug)
                seen_slugs[key] = geoname_id

                fields = {
                    "region": region,
                    "name": name,
                    "slug": slug,
                    "type": (row.get("type") or "населённый пункт").strip()[:64],
                    "latitude": _dec(row.get("latitude")),
                    "longitude": _dec(row.get("longitude")),
                    "population": max(0, _int(row.get("population"))),
                    "timezone": (row.get("timezone") or "")[:64],
                    "is_active": True,
                    "geoname_id": geoname_id,
                }

                obj = existing.get(geoname_id)
                if obj is None:
                    to_create.append(Settlement(**fields))
                    created += 1
                else:
                    changed = False
                    for attr, value in fields.items():
                        if getattr(obj, attr) != value:
                            setattr(obj, attr, value)
                            changed = True
                    if changed:
                        to_update.append(obj)
                        updated += 1

                if len(to_create) >= BATCH:
                    Settlement.objects.bulk_create(to_create, batch_size=BATCH)
                    to_create.clear()
                if len(to_update) >= BATCH:
                    Settlement.objects.bulk_update(
                        to_update,
                        [
                            "region",
                            "name",
                            "slug",
                            "type",
                            "latitude",
                            "longitude",
                            "population",
                            "timezone",
                            "is_active",
                        ],
                        batch_size=BATCH,
                    )
                    to_update.clear()

        if to_create:
            Settlement.objects.bulk_create(to_create, batch_size=BATCH)
        if to_update:
            Settlement.objects.bulk_update(
                to_update,
                [
                    "region",
                    "name",
                    "slug",
                    "type",
                    "latitude",
                    "longitude",
                    "population",
                    "timezone",
                    "is_active",
                ],
                batch_size=BATCH,
            )
        return {"created": created, "updated": updated, "skipped": skipped}

    def _upsert_legacy_chechnya(self) -> dict:
        """Ensure legacy CHECHNYA_SETTLEMENTS slugs exist for existing Post.city values."""
        region = Region.objects.filter(code="12").first()
        if region is None:
            return {"created": 0, "updated": 0}
        created = updated = 0
        # GeoNames identifies Grozny by this ID. Fix it before adding legacy
        # aliases so the unique (region, slug) constraint stays satisfied.
        grozny = Settlement.objects.filter(geoname_id=558418).first()
        if grozny:
            # The unique constraint requires removing a conflicting legacy
            # row before assigning the canonical slug to the GeoNames row.
            Settlement.objects.filter(region=region, slug="grozny").exclude(
                pk=grozny.pk
            ).delete()
            changes = (
                grozny.name != "Грозный"
                or grozny.slug != "grozny"
                or grozny.region_id != region.id
            )
            grozny.name = "Грозный"
            grozny.slug = "grozny"
            grozny.region = region
            grozny.save(update_fields=["name", "slug", "region", "updated_at"])
            if changes:
                updated += 1

        for slug, name in CHECHNYA_SETTLEMENTS.items():
            obj, was_created = Settlement.objects.update_or_create(
                region=region,
                slug=slug,
                defaults={
                    "name": name,
                    "type": "населённый пункт",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated}

    def _mark_popular(self) -> int:
        Settlement.objects.filter(is_popular=True).update(is_popular=False)
        return Settlement.objects.filter(
            geoname_id__in=POPULAR_SETTLEMENT_GEONAMES
        ).update(is_popular=True)
