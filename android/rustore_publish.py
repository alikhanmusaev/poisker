#!/usr/bin/env python3
"""Publish the Poisker Android APK to RuStore.

Auth uses keyId + RSA-SHA512 signature as described at:
https://www.rustore.ru/help/work-with-rustore-api/api-authorization-token

The private key file contains only the PKCS#8 body. keyId is taken from
RUSTORE_KEY_ID or a sibling file named "rustore key id.txt".
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
LISTING_PATH = ANDROID / "store" / "listing.json"
DEFAULT_KEY = Path(r"C:\Users\a\Desktop\поискер ключ.txt")
DEFAULT_KEY_ID = Path(r"C:\Users\a\Desktop\rustore key id.txt")
API = "https://public-api.rustore.ru"
PACKAGE = "ru.poisker.app"


def _openssl() -> str:
    candidates = [
        os.environ.get("OPENSSL_EXE"),
        r"C:\Program Files\Git\usr\bin\openssl.exe",
        "openssl",
    ]
    for item in candidates:
        if not item:
            continue
        try:
            subprocess.run(
                [item, "version"],
                check=True,
                capture_output=True,
                text=True,
            )
            return item
        except (OSError, subprocess.CalledProcessError):
            continue
    raise SystemExit("openssl не найден. Установите Git for Windows или OpenSSL.")


def _private_key_pem(raw: str) -> str:
    body = "".join(raw.split())
    if "BEGIN" in raw:
        return raw.strip() + "\n"
    lines = [body[i : i + 64] for i in range(0, len(body), 64)]
    return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END PRIVATE KEY-----\n"


def _timestamp() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sign(openssl: str, key_id: str, timestamp: str, pem: str) -> str:
    message = f"{key_id}{timestamp}".encode("utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as handle:
        handle.write(pem)
        pem_path = handle.name
    try:
        completed = subprocess.run(
            [openssl, "dgst", "-sha512", "-sign", pem_path],
            input=message,
            check=True,
            capture_output=True,
        )
    finally:
        os.unlink(pem_path)
    return base64.b64encode(completed.stdout).decode("ascii")


def _request(method: str, url: str, token: str | None = None, data=None, headers=None):
    hdrs = dict(headers or {})
    if token:
        hdrs["Public-Token"] = token
    body = None
    if data is not None and not isinstance(data, (bytes, bytearray)):
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif isinstance(data, (bytes, bytearray)):
        body = data
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {url}\n{detail}") from exc


def _curl_upload(token: str, url: str, files: list[tuple[str, Path]]):
    cmd = [
        "curl",
        "--fail-with-body",
        "-sS",
        "-X",
        "POST",
        url,
        "-H",
        f"Public-Token: {token}",
    ]
    for field, path in files:
        cmd.extend(["-F", f"{field}=@{path}"])
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(
            f"curl failed {url}\n{completed.stdout}\n{completed.stderr}"
        )
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


def _load_key_id(args) -> str:
    if args.key_id:
        return str(args.key_id).strip()
    env_id = os.environ.get("RUSTORE_KEY_ID", "").strip()
    if env_id:
        return env_id
    if DEFAULT_KEY_ID.exists():
        return DEFAULT_KEY_ID.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "Нужен ID ключа RuStore (не сам приватный ключ).\n"
        "Скопируйте ID из Консоли: Компания/Разработчик → API RuStore → столбец ID.\n"
        "Затем: set RUSTORE_KEY_ID=123456  или сохраните в "
        r"C:\Users\a\Desktop\rustore key id.txt"
    )


def auth(openssl: str, key_id: str, pem: str) -> str:
    timestamp = _timestamp()
    signature = _sign(openssl, key_id, timestamp, pem)
    payload = {"keyId": key_id, "timestamp": timestamp, "signature": signature}
    result = _request("POST", f"{API}/public/auth/", data=payload)
    if result.get("code") != "OK":
        raise SystemExit(f"Auth failed: {json.dumps(result, ensure_ascii=False)}")
    return result["body"]["jwe"]


def _log(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--key-id")
    parser.add_argument("--apk", type=Path, default=ANDROID / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk")
    parser.add_argument("--icon", type=Path, default=ROOT / "static" / "icons" / "icon-512.png")
    parser.add_argument("--screenshots", type=Path, default=ANDROID / "store" / "screenshots")
    parser.add_argument("--commit", action="store_true", help="Отправить черновик на модерацию")
    args = parser.parse_args()

    if not args.key_file.exists():
        raise SystemExit(f"Нет файла ключа: {args.key_file}")
    if not args.apk.exists():
        raise SystemExit(f"Нет APK: {args.apk}. Сначала соберите android/assembleRelease.")

    listing = json.loads(LISTING_PATH.read_text(encoding="utf-8"))
    listing.pop("packageName", None)
    openssl = _openssl()
    pem = _private_key_pem(args.key_file.read_text(encoding="utf-8"))
    key_id = _load_key_id(args)
    token = auth(openssl, key_id, pem)
    _log("JWE token OK")

    apps = _request("GET", f"{API}/public/v1/application", token=token)
    content = (apps.get("body") or {}).get("content") or []
    _log("Apps: " + json.dumps(content, ensure_ascii=True, indent=2))
    packages = {item.get("packageName") for item in content if item.get("packageName")}
    if PACKAGE not in packages:
        unnamed = [item for item in content if not item.get("packageName")]
        if unnamed:
            _log(
                f"Found app without packageName (appId={unnamed[0].get('appId')}); "
                f"uploading as {PACKAGE}"
            )
        else:
            raise SystemExit(
                f"No app {PACKAGE} in RuStore yet. Create it in https://console.rustore.ru/ "
                "with package name ru.poisker.app, then re-run."
            )

    created = _request(
        "POST",
        f"{API}/public/v1/application/{PACKAGE}/version",
        token=token,
        data=listing,
    )
    version_id = created.get("body")
    if not version_id:
        raise SystemExit(f"Не удалось создать черновик: {json.dumps(created, ensure_ascii=False)}")
    _log(f"versionId {version_id}")

    _log("Uploading APK...")
    _log(json.dumps(_curl_upload(
            token,
            f"{API}/public/v1/application/{PACKAGE}/version/{version_id}/apk?isMainApk=true&servicesType=Unknown",
            [("file", args.apk)],
        ), ensure_ascii=True))
    _log("Uploading icon...")
    _log(json.dumps(_curl_upload(
            token,
            f"{API}/public/v1/application/{PACKAGE}/version/{version_id}/image/icon",
            [("file", args.icon)],
        ), ensure_ascii=True))
    shots = sorted(args.screenshots.glob("*.png")) + sorted(args.screenshots.glob("*.jpg"))
    if len(shots) < 3:
        raise SystemExit(f"Need at least 3 screenshots in {args.screenshots}")
    _log("Uploading screenshots...")
    _log(json.dumps(_curl_upload(
            token,
            f"{API}/public/v1/application/{PACKAGE}/version/{version_id}/screens?deviceType=MOBILE",
            [("files", path) for path in shots[:8]],
        ), ensure_ascii=True))
    if args.commit:
        committed = _request(
            "POST",
            f"{API}/public/v1/application/{PACKAGE}/version/{version_id}/commit",
            token=token,
        )
        _log("Submitted: " + json.dumps(committed, ensure_ascii=True))
    else:
        _log("Draft ready. Re-run with --commit to send to moderation.")


if __name__ == "__main__":
    sys.exit(main())
