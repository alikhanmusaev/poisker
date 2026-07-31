"""Unit tests for GeoNames CSV builder (no Django DB required for pure helpers)."""

from pathlib import Path

from locations.services.build_csv import write_regions, write_settlements
from locations.slugify import slugify_ru


def test_write_regions_uses_russian_names(tmp_path: Path):
    admin1 = tmp_path / "admin1.txt"
    admin1.write_text(
        "RU.12\tChechnya\tChechnya\t584711\n"
        "RU.00\tRussia\tRussia\t2017370\n",
        encoding="utf-8",
    )
    out = tmp_path / "regions.csv"
    count = write_regions(admin1, out)
    assert count == 1
    text = out.read_text(encoding="utf-8")
    assert "Чеченская Республика" in text
    assert "chechenskaya-respublika" in text


def test_write_settlements_skips_latin_only(tmp_path: Path):
    settlements = {
        558418: {
            "geoname_id": 558418,
            "name": "Groznyy",
            "fcode": "PPLA",
            "region_code": "12",
            "latitude": "43.3",
            "longitude": "45.6",
            "population": 300000,
            "timezone": "Europe/Moscow",
        },
        1: {
            "geoname_id": 1,
            "name": "LatinOnly",
            "fcode": "PPL",
            "region_code": "12",
            "latitude": "43.0",
            "longitude": "45.0",
            "population": 2000,
            "timezone": "Europe/Moscow",
        },
    }
    ru_names = {558418: "Грозный"}
    out = tmp_path / "settlements.csv"
    count = write_settlements(settlements, ru_names, out)
    assert count == 1
    text = out.read_text(encoding="utf-8")
    assert "Грозный" in text
    assert slugify_ru("Грозный") in text
    assert "LatinOnly" not in text
