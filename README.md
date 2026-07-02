# Поискер — доска объявлений (poisker.ru)

Региональная доска объявлений **Поискер** для **Чеченской Республики** — [poisker.ru](https://poisker.ru).

## Возможности

- Публикация без регистрации (телефон + 1 объявление в сутки)
- Пошаговая публикация с сохранением секретной ссылки
- Редактирование по секретной ссылке (кнопка «Редактировать» на своих объявлениях)
- Умный поиск (Typesense) с опечатками и синонимами
- Сортировка: рекомендуемые, по релевантности, по дате, **по дешевле / по дороже**
- Фильтры: с фото, с ценой
- Слайдер и увеличение фото на странице объявления
- Ранжированная лента
- «Мои объявления» — сохранённые ссылки на устройстве
- Жалобы и админ-модерация
- Платное поднятие объявлений
- PWA (Jinja2 + HTMX + Service Worker)

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d postgres redis typesense minio
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python generate_icons.py
python download_vendor_assets.py
python manage.py
flask --app wsgi run --debug
```

Откройте http://127.0.0.1:5000

Админка: http://127.0.0.1:5000/admin (логин/пароль из `.env`)

Демо-объявления (16 шт.) создаются при `python manage.py`. Повторно: `python manage.py seed --force`.

## Docker (локально)

```bash
cp .env.example .env
docker compose build web
docker compose up -d
```

По умолчанию в Docker используется `FLASK_ENV=development` — dev-секреты допустимы для локальной разработки.

Приложение: http://localhost/ (nginx) или http://127.0.0.1:8000/ (web напрямую)

После изменений в коде:

```bash
docker compose build web && docker compose up -d web
```

## Docker (production)

1. Скопируйте шаблон: `cp .env.production.example .env`
2. Заполните **обязательные** переменные (см. ниже)
3. Запуск:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build web
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

В production наружу смотрит только **nginx** (порт 80). Postgres, Redis, Typesense и MinIO доступны только внутри Docker-сети.

Включены: `FLASK_ENV=production`, `SESSION_COOKIE_SECURE=true`, `REQUIRE_CAPTCHA=true`, `HSTS_ENABLED=true`, `TRUST_PROXY=true`.

### Обязательные переменные для production

| Переменная | Описание |
|------------|----------|
| `SECRET_KEY` | Секрет Flask-сессий |
| `HMAC_SECRET` | HMAC для хешей телефона и IP |
| `PHONE_ENCRYPTION_KEY` | Ключ шифрования телефонов (отдельно от HMAC) |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `ADMIN_PASSWORD` | Пароль админки |
| `TYPESENSE_API_KEY` | API-ключ Typesense |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Учётные данные MinIO |
| `S3_PUBLIC_URL` | Публичный URL медиа (HTTPS) |
| `CAPTCHA_PROVIDER` | `builtin` (по умолчанию), `yandex`, `turnstile`, `none` |
| `REQUIRE_CAPTCHA` | Требовать капчу при публикации и жалобах |

Полный список — в `.env.production.example`.

## Резервное копирование

См. [`docs/BACKUP.md`](docs/BACKUP.md) — PostgreSQL, MinIO, volumes и график бэкапов.

## Стек

- Flask, SQLAlchemy, PostgreSQL
- Typesense, Redis, MinIO
- HTMX, Service Worker
- APScheduler (ранжирование, истечение объявлений, очистка удалённых)

## Deleted posts cleanup

Пользовательское действие **«Снять объявление»** — это soft delete:

- объявление сразу исчезает из публичной выдачи и поиска;
- запись в PostgreSQL, картинки в MinIO и зашифрованный телефон временно сохраняются;
- через `DELETED_POST_RETENTION_DAYS` дней (по умолчанию 30) фоновый cleanup удаляет картинки из MinIO и очищает `phone_encrypted`;
- строка в базе остаётся для истории модерации (`phone_hash`, `phone_masked`, заголовок и т.д.).

Ручной запуск:

```bash
flask --app wsgi cleanup-deleted-posts --days 30 --batch-size 100
```

Автоматический запуск — ежедневно в 03:30 (Europe/Moscow) при `SCHEDULER_ENABLED=true`.

Переменные окружения:

- `DELETED_POST_RETENTION_DAYS=30`
- `DELETED_POST_CLEANUP_BATCH_SIZE=100`
- Nginx + Gunicorn (см. `nginx.conf`, `Dockerfile`)

## Переменные окружения

См. `.env.example`

Перед продакшеном:
- `SECRET_KEY`, `HMAC_SECRET`, `PHONE_ENCRYPTION_KEY` — сильные случайные значения (`PHONE_ENCRYPTION_KEY` ≠ `HMAC_SECRET`)
- `REQUIRE_CAPTCHA=true` — встроенная математическая капча, внешние ключи не нужны
- `APP_DOMAIN=poisker.ru`, `SITE_NAME=Поискер` — для SEO, PWA и Google Play asset links

## Структура

```
app/
  models/      — Post, Report, Promotion, AdminUser
  services/    — phone, posts, search, ranking, storage
  routes/      — main, posts, search, admin, reports, promotions
  templates/   — Jinja2 + HTMX partials
  static/      — CSS, JS, sw.js, manifest
```

## Политика конфиденциальности

`/privacy` — страница для соответствия 152-ФЗ и Google Play Data safety.  
Также: `/terms`, `/guidelines`.

## Публикация в Google Play

См. подробный чеклист: [`docs/GOOGLE_PLAY.md`](docs/GOOGLE_PLAY.md)

- PWA + TWA (Bubblewrap), Digital Asset Links: `/.well-known/assetlinks.json`
- Service Worker: `/sw.js`
- Maskable icons в `app/static/icons/`
- Переменные: `APP_DOMAIN`, `ANDROID_PACKAGE_NAME`, `ANDROID_SHA256_FINGERPRINTS`, `SUPPORT_EMAIL`
