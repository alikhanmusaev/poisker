# Публикация в Google Play

Сервис **«Поискер»** ([poisker.ru](https://poisker.ru)) публикуется как **PWA через Trusted Web Activity (TWA)** — нативная оболочка Android открывает ваш HTTPS-сайт в полноэкранном режиме без адресной строки.

## Предварительные требования

- Домен **poisker.ru** с **HTTPS** (Let's Encrypt или Cloudflare)
- Политика конфиденциальности: `https://poisker.ru/privacy`
- Условия: `https://poisker.ru/terms`
- Правила UGC: `https://poisker.ru/guidelines`
- Контакт поддержки в `.env`: `SUPPORT_EMAIL`

## Переменные окружения

```env
APP_DOMAIN=poisker.ru
SITE_NAME=Поискер
ANDROID_PACKAGE_NAME=ru.poisker.app
ANDROID_SHA256_FINGERPRINTS=AA:BB:CC:...
SUPPORT_EMAIL=support@poisker.ru
```

Отпечаток SHA-256 ключа подписи AAB:

```bash
keytool -list -v -keystore upload-keystore.jks -alias upload
```

## Digital Asset Links

После деплоя проверьте:

```
https://poisker.ru/.well-known/assetlinks.json
```

Должен вернуть JSON с `package_name` и `sha256_cert_fingerprints`. Проверка Google:

https://developers.google.com/digital-asset-links/tools/generator

## Сборка TWA (Bubblewrap)

```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest https://poisker.ru/static/manifest.webmanifest
bubblewrap build
```

При инициализации укажите тот же `package_name`, что в `ANDROID_PACKAGE_NAME`.

## Чеклист Google Play Console

### Store listing
- [ ] Название: «Поискер»
- [ ] Краткое описание (до 80 символов)
- [ ] Полное описание на русском
- [ ] Иконка 512×512 (`app/static/icons/icon-512.png`)
- [ ] Feature graphic 1024×500
- [ ] Скриншоты телефона (мин. 2), планшета (рекомендуется)
- [ ] Категория: Shopping или Lifestyle
- [ ] Контактный email (`SUPPORT_EMAIL`)
