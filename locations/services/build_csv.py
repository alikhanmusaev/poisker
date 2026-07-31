"""Pure helpers to build regions/settlements CSV from GeoNames dumps."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlretrieve

from locations.region_names import REGION_RU_NAMES, REGION_SLUG_OVERRIDES
from locations.slugify import slugify_ru

DATA_DIR = Path("locations/data")
GEONAMES_BASE = "https://download.geonames.org/export/dump"

FEATURE_TYPE_RU = {
    "PPLC": "город",
    "PPLA": "город",
    "PPLA2": "город",
    "PPLA3": "город",
    "PPLA4": "город",
    "PPL": "населённый пункт",
    "PPLX": "район города",
    "PPLS": "населённый пункт",
    "STLMT": "поселение",
}

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_ADMIN_SEATS = {"PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4"}


def _has_cyrillic(value: str) -> bool:
    return bool(_CYRILLIC_RE.search(value or ""))


def _ensure(path: Path, url: str, log: Callable[[str], None]) -> None:
    if path.exists() and path.stat().st_size > 0:
        log(f"Using existing {path.name}")
        return
    log(f"Downloading {url} …")
    urlretrieve(url, path)


def read_ru_settlements(cities_zip: Path, min_population: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    with zipfile.ZipFile(cities_zip) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".txt"))
        with zf.open(name) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 19:
                    continue
                if parts[8] != "RU":
                    continue
                fcode = parts[7]
                try:
                    population = int(parts[14] or 0)
                except ValueError:
                    population = 0
                if population < min_population and fcode not in _ADMIN_SEATS:
                    continue
                geoname_id = int(parts[0])
                admin1 = (parts[10] or "").strip()
                if not admin1 or admin1 in {"00", "JA"}:
                    continue
                out[geoname_id] = {
                    "geoname_id": geoname_id,
                    "name": parts[1],
                    "asciiname": parts[2],
                    "latitude": parts[4],
                    "longitude": parts[5],
                    "fcode": fcode,
                    "region_code": admin1,
                    "population": population,
                    "timezone": parts[17],
                }
    return out


def load_ru_alternate_names(
    alt_zip: Path, geoname_ids: set[int]
) -> dict[int, str]:
    best: dict[int, tuple[int, str]] = {}
    with zipfile.ZipFile(alt_zip) as zf:
        name = next(n for n in zf.namelist() if "alternateNames" in n)
        with zf.open(name) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                if parts[2] != "ru":
                    continue
                try:
                    gid = int(parts[1])
                except ValueError:
                    continue
                if gid not in geoname_ids:
                    continue
                alt = (parts[3] or "").strip()
                if not alt or not _has_cyrillic(alt):
                    continue
                preferred = 2 if len(parts) > 4 and parts[4] == "1" else 0
                short = 1 if len(parts) > 5 and parts[5] == "1" else 0
                score = preferred * 10 + short
                score = score * 1000 + min(len(alt), 80)
                prev = best.get(gid)
                if prev is None or score > prev[0]:
                    best[gid] = (score, alt)
    return {gid: value for gid, (_score, value) in best.items()}


def write_regions(admin1_path: Path, out_path: Path) -> int:
    rows = []
    with admin1_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("RU."):
                continue
            parts = line.rstrip("\n").split("\t")
            code = parts[0].split(".", 1)[1]
            if code in {"00", "JA"} or code not in REGION_RU_NAMES:
                continue
            name = REGION_RU_NAMES[code]
            slug = REGION_SLUG_OVERRIDES.get(code) or slugify_ru(name)
            geoname_id = parts[3] if len(parts) > 3 else ""
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "slug": slug,
                    "geoname_id": geoname_id,
                    "federal_district": "",
                }
            )
    rows.sort(key=lambda r: r["name"])
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["code", "name", "slug", "geoname_id", "federal_district"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def write_settlements(
    settlements: dict[int, dict],
    ru_names: dict[int, str],
    out_path: Path,
) -> int:
    fieldnames = [
        "region_code",
        "region_name",
        "name",
        "type",
        "slug",
        "geoname_id",
        "fias_id",
        "latitude",
        "longitude",
        "population",
        "timezone",
    ]
    rows = []
    for gid, row in settlements.items():
        code = row["region_code"]
        if code not in REGION_RU_NAMES:
            continue
        name = ru_names.get(gid) or row["name"]
        if not _has_cyrillic(name):
            continue
        rows.append(
            {
                "region_code": code,
                "region_name": REGION_RU_NAMES[code],
                "name": name,
                "type": FEATURE_TYPE_RU.get(row["fcode"], "населённый пункт"),
                "slug": slugify_ru(name),
                "geoname_id": gid,
                "fias_id": "",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "population": row["population"],
                "timezone": row["timezone"],
            }
        )
    rows.sort(key=lambda r: (-int(r["population"] or 0), r["name"]))
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_locations_csv(
    *,
    data_dir: Path = DATA_DIR,
    min_population: int = 1000,
    skip_download: bool = False,
    log: Callable[[str], None] | None = None,
) -> dict:
    log = log or (lambda _msg: None)
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    admin1 = data_dir / "admin1CodesASCII.txt"
    cities_zip = data_dir / "cities1000.zip"
    alt_zip = data_dir / "alternateNamesV2.zip"

    if not skip_download:
        _ensure(admin1, f"{GEONAMES_BASE}/admin1CodesASCII.txt", log)
        _ensure(cities_zip, f"{GEONAMES_BASE}/cities1000.zip", log)
        _ensure(alt_zip, f"{GEONAMES_BASE}/alternateNamesV2.zip", log)

    for path in (admin1, cities_zip, alt_zip):
        if not path.exists():
            raise FileNotFoundError(f"Missing dump: {path}")

    settlements = read_ru_settlements(cities_zip, min_population)
    log(f"RU settlements from cities1000: {len(settlements)}")

    ru_names = load_ru_alternate_names(alt_zip, set(settlements))
    log(f"Russian alternate names matched: {len(ru_names)}")

    regions_path = data_dir / "regions.csv"
    settlements_path = data_dir / "settlements.csv"
    region_count = write_regions(admin1, regions_path)
    settlement_count = write_settlements(settlements, ru_names, settlements_path)

    return {
        "regions": region_count,
        "settlements": settlement_count,
        "regions_path": regions_path,
        "settlements_path": settlements_path,
    }
