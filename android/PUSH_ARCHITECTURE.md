# Push architecture (Poisker)

## Overview

Android WebView shell + Django session auth + FCM data messages.

```
[Django event] → schedule_push (on_commit)
       → Firebase Admin SDK → FCM
       → PoiskerFirebaseMessagingService / system tray
       → MainActivity Intent extra → WebView.loadUrl(safeUrl)
```

Token registration does **not** use `JavascriptInterface`.

## Device registration

1. App obtains FCM token (`FirebaseMessaging` / `onNewToken`).
2. `PushTokenSyncWorker` (WorkManager) POSTs to `/api/v1/push/devices/`.
3. Auth: WebView `CookieManager` cookies (`sessionid` + `csrftoken`) on OkHttp:
   - `Cookie`
   - `X-CSRFToken`
   - `Referer: https://poisker.ru/`
4. Body: `token`, `platform=android`, `device_id` (UUID in DataStore), `app_version`, `app_build`.
5. Logout: `DELETE /api/v1/push/devices/current/?device_id=…` (only current device).

If cookie/CSRF registration proves unreliable in production, use a short-lived one-time registration code (1–5 min, store hash only) from an authenticated Django page — **not** a JS bridge. Not implemented yet; session+CSRF is the primary path.

## Payload (data)

```json
{
  "type": "message",
  "title": "Новое сообщение",
  "body": "…",
  "url": "https://poisker.ru/messages/<uuid>/",
  "entity_id": "<uuid>"
}
```

Types: `message`, `listing_approved`, `listing_rejected`, `listing_expiring`, `listing_expired`, `system` (+ `marketing` gated separately).

URLs must be `https` + `poisker.ru` / `www` / `*.poisker.ru`. Invalid → `https://poisker.ru/`.

## Preference gates

`NotificationPreference`: messages / listings / system (default on), marketing (default **off**).

## Event sources

| Event | Hook |
|-------|------|
| Moderation / expire / in-app notify | `bookmarks.services._notify_user` → `push_for_bookmark_notification` |
| New message (not to sender) | `messaging.services.send_message` → `push_for_new_message` |
| Listing expiring (≤3 days) | APScheduler job `listing_expiring_push` |

No push from `Model.save()` duplicates; use service layer + `transaction.on_commit`.

## Android navigation

- `launchMode=singleTop`
- PendingIntent → `MainActivity` + `EXTRA_URL`
- Cold start / `onNewIntent` / already open → load in existing WebView
- Channels: `messages` (HIGH), `listings` (DEFAULT), `system` (DEFAULT)
- Small icon: monochrome `ic_stat_poisker`
- `POST_NOTIFICATIONS` requested after session cookies present (not on every cold start)

## Server

App: `notifications/` — `PushDevice`, preferences, Admin SDK, `send_test_push`.
