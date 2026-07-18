# Poisker Flutter client

Native Flutter app (`ru.poisker.app`) → Django REST API `https://poisker.ru/api/v1/`.

Replaces the Kotlin WebView shell (`../android/`) as the primary mobile client.

## Features

- Guest feed + listing detail; JWT login / register / password reset
- Filters: city, category, sort
- Create / edit listing (multipart photos, draft, submit, republish)
- My listings, bookmarks, profile edit
- Chats with polling + unread badge
- FCM registration, preferences, deep links into chat/listing
- Privacy / terms links

## Run

```bash
cd mobile
flutter pub get
flutter run
```

## Architecture

| Path | Role |
|------|------|
| `lib/core/api/` | Dio, models, repositories |
| `lib/core/auth/` | Tokens + AuthController |
| `lib/core/router/` | go_router shell + auth gates |
| `lib/features/` | Screens |
| `lib/push/` | FCM + local notifications |

## Play / release

See [PLAY_RELEASE.md](PLAY_RELEASE.md). Upload keystore is still owner-side.

## Relation to `android/`

| Path | Status |
|------|--------|
| `mobile/` | Active Flutter + API |
| `android/` | Legacy WebView |

Same `applicationId` so FCM / Play stay continuous.
