"""Trusted Web Activity identity for the Poisker Android app on RuStore."""

PACKAGE_NAME = "ru.poisker.app"
SITE_URL = "https://poisker.ru"

# SHA-256 of the upload/release signing certificate (colon-separated hex).
# Filled after android/keystore/poisker-upload.jks is generated.
CERT_SHA256_FINGERPRINTS = [
    "65:33:64:11:9C:04:7B:A1:56:33:03:06:F6:E7:69:7D:5D:E7:1F:9B:3D:85:AA:FE:57:0D:F9:83:D8:FF:F9:20",
]


def asset_links():
    fingerprints = [
        value.strip()
        for value in CERT_SHA256_FINGERPRINTS
        if value and "PLACEHOLDER" not in value
    ]
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": PACKAGE_NAME,
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
