"""Build regions.csv + settlements.csv from GeoNames dumps.

Downloads (if missing) into locations/data/:
  - admin1CodesASCII.txt
  - cities1000.zip
  - alternateNamesV2.zip (for Russian display names)

Usage:
  python manage.py build_locations_csv
  python manage.py build_locations_csv --min-population 1000
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from locations.services.build_csv import DATA_DIR, build_locations_csv


class Command(BaseCommand):
    help = "Build locations/data/{regions,settlements}.csv from GeoNames."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=str(DATA_DIR),
            help="Directory for dumps and output CSV",
        )
        parser.add_argument(
            "--min-population",
            type=int,
            default=1000,
            help="Keep settlements with population >= N (admin seats kept anyway)",
        )
        parser.add_argument(
            "--skip-download",
            action="store_true",
            help="Do not download missing dumps",
        )

    def handle(self, *args, **options):
        result = build_locations_csv(
            data_dir=Path(options["data_dir"]),
            min_population=options["min_population"],
            skip_download=options["skip_download"],
            log=self.stdout.write,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {result['regions']} regions → {result['regions_path']}; "
                f"{result['settlements']} settlements → {result['settlements_path']}"
            )
        )
