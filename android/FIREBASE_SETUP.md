# Firebase setup (Poisker Android)

## Project

| Field | Value |
|-------|--------|
| Project display name | poisker |
| **Project ID** | `poisker-84437` |
| Created or reused | **Existing** (not duplicated) |
| Android package | `ru.poisker.app` |
| Android display name | Poisker Android |
| **Firebase App ID** | `1:1055213565369:android:8335551a7cdbacb7abb268` |
| Config file | `android/app/google-services.json` |

## CLI commands used

```bash
firebase --version
firebase login:list
firebase projects:list
firebase use poisker-84437
firebase apps:list
firebase apps:sdkconfig ANDROID 1:1055213565369:android:8335551a7cdbacb7abb268
firebase apps:android:sha:list 1:1055213565369:android:8335551a7cdbacb7abb268
firebase apps:android:sha:create <APP_ID> <SHA>
```

Root helpers: `.firebaserc` → default project `poisker-84437`.

## Gradle

- Plugin: `com.google.gms.google-services` (`libs.plugins.google.services`)
- BoM: `com.google.firebase:firebase-bom` **33.7.0**
- Dependency: `com.google.firebase:firebase-messaging` (not `messaging-ktx`)
- Analytics: **not** added

## SHA fingerprints registered

Debug only (release keystore not configured yet):

| Type | Hash (colon form) |
|------|-------------------|
| SHA-1 | `5E:27:81:F3:C2:D1:BF:21:12:77:F2:C1:C1:47:3F:4D:9A:5A:0F:D6` |
| SHA-256 | `2A:0E:76:5E:94:69:3E:9E:13:BC:52:F0:57:FA:0D:92:1D:8B:6B:DD:04:0A:47:4F:1D:D8:9F:9A:54:7C:B7:FB` |

See `FIREBASE_RELEASE_SETUP.md` for upload / Play App Signing SHA.

## Server credentials (Django)

Never commit service-account JSON.

Env (see `.env.example`):

```
FIREBASE_PROJECT_ID=poisker-84437
FIREBASE_CREDENTIALS_FILE=/secure/path/firebase-adminsdk.json
FCM_ENABLED=true
```

Optional ADC: `FCM_USE_ADC=true` or `GOOGLE_APPLICATION_CREDENTIALS`.

## Test push

```bash
python manage.py send_test_push <user_id>          # DEBUG
python manage.py send_test_push <user_id> --force  # production, explicit
```

## Do not commit

- Service account private key JSON
- `keystore.properties`, `*.jks`, `*.keystore`
- Full FCM tokens, session cookies, CSRF tokens in logs/docs
