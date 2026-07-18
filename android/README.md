# Poisker Android (WebView shell)

> **Статус:** legacy. Активный клиент — Flutter в [`../mobile/`](../mobile/) (тот же `ru.poisker.app`).

Нативное приложение-оболочка для мобильного сайта [https://poisker.ru/](https://poisker.ru/).

- **Package / applicationId:** `ru.poisker.app`
- **Версия:** `1.0` (`versionCode` 1)
- **Min SDK:** 24 · **Target / Compile SDK:** 35
- **UI:** Jetpack Compose + Android WebView

## Архитектура

Первая стабильная версия для Google Play открывает сайт внутри безопасного WebView.
Django REST API (`/api/v1/`) **сохранён** на backend и не используется этой оболочкой.
Позже экраны можно постепенно переводить на API:

1. главная  
2. карточка объявления  
3. создание объявления  
4. профиль  
5. сообщения  
6. push-уведомления (FCM + Django `notifications`) — **реализовано** в WebView-оболочке

Резервная копия до FCM: `/home/a/Projects/Poisker_backup_before_webview_fcm`  
Ветка: `android-webview-fcm`

## Запуск (debug)

```bash
cd android
./gradlew clean assembleDebug
./gradlew installDebug   # при подключённом устройстве/эмуляторе
```

APK: `app/build/outputs/apk/debug/app-debug.apk`

Стартовый URL: `https://poisker.ru/`

## Тесты и lint

```bash
./gradlew test
./gradlew lint
```

## Release / AAB

1. Создайте upload keystore (если ещё нет):

```bash
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

2. Скопируйте `keystore.properties.example` → `keystore.properties` и заполните поля.

3. Соберите bundle:

```bash
./gradlew :app:bundleRelease
```

AAB: `app/build/outputs/bundle/release/app-release.aab`

Без реального `keystore.properties` release **не подписывается** фиктивным ключом.

## Android App Links

Manifest объявляет `https://poisker.ru` и `https://www.poisker.ru` с `android:autoVerify="true"`.

Файл на сайте: `https://poisker.ru/.well-known/assetlinks.json`

| Ключ | SHA-256 |
|------|---------|
| Debug (`androiddebugkey`) | `2A:0E:76:5E:94:69:3E:9E:13:BC:52:F0:57:FA:0D:92:1D:8B:6B:DD:04:0A:47:4F:1D:D8:9F:9A:54:7C:B7:FB` |
| Release upload | получить: `keytool -list -v -keystore upload-keystore.jks` |
| Play App Signing | после включения в Play Console → Setup → App integrity (использовать **app signing** fingerprint, не только upload) |

Опционально: env `ANDROID_RELEASE_SHA256` на сервере Django добавит fingerprint в `assetlinks.json`.

## Permissions

- `INTERNET`
- `ACCESS_NETWORK_STATE`
- `CAMERA` (runtime, только при capture в `<input type=file capture>`)
- `POST_NOTIFICATIONS` (runtime на Android 13+, после входа / session cookie)

## Push (FCM)

- Firebase project: `poisker-84437` (см. [FIREBASE_SETUP.md](FIREBASE_SETUP.md))
- Регистрация токена на Django: `POST /api/v1/push/devices/` (session cookie + CSRF)
- Архитектура: [PUSH_ARCHITECTURE.md](PUSH_ARCHITECTURE.md)
- Release SHA: [FIREBASE_RELEASE_SETUP.md](FIREBASE_RELEASE_SETUP.md)

## Возможности оболочки

- Django session cookies (CookieManager + flush)
- Выбор файлов / Photo Picker / камера через FileProvider
- tel: → `ACTION_DIAL`; WhatsApp / Telegram / внешние HTTPS → Intent
- DownloadManager для HTTPS-файлов
- Back: `WebView.goBack()` → иначе закрытие Activity
- Pull-to-refresh (только если `scrollY == 0`)
- Offline / ошибка загрузки / SSL cancel (без `handler.proceed()`)
- FCM: каналы messages / listings / system; открытие URL в WebView
- User-Agent suffix: `PoiskerAndroid/1.0`
- Сохранение WebView state при повороте (`configChanges` + `saveState`)

## Документы

- [FIREBASE_SETUP.md](FIREBASE_SETUP.md)
- [PUSH_ARCHITECTURE.md](PUSH_ARCHITECTURE.md)
- [FIREBASE_RELEASE_SETUP.md](FIREBASE_RELEASE_SETUP.md)
- [PLAY_STORE_CHECKLIST.md](PLAY_STORE_CHECKLIST.md)
- [PRIVACY_AND_DATA_SAFETY.md](PRIVACY_AND_DATA_SAFETY.md)
- Политика сайта: https://poisker.ru/privacy
