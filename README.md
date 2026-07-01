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

По умолчанию в Docker используется `FLASK_ENV=development` из `.env` — так стек поднимается с dev-секретами (minioadmin, typesenseKey).

Для **продакшена** в `.env` задайте `FLASK_ENV=production`, сильные `SECRET_KEY` / `HMAC_SECRET`, ключи Turnstile и `REQUIRE_TURNSTILE=true`.

Приложение: http://localhost:8000

После изменений в коде:

```bash
docker compose build web && docker compose up -d web
```

## Стек

- Flask, SQLAlchemy, PostgreSQL
- Typesense, Redis, MinIO
- HTMX, Service Worker
- APScheduler (ранжирование, истечение объявлений)
- Nginx + Gunicorn (см. `nginx.conf`, `Dockerfile`)

## Переменные окружения

См. `.env.example`

Перед продакшеном:
- `SECRET_KEY`, `HMAC_SECRET` — сильные случайные значения
- `REQUIRE_TURNSTILE=true` и ключи Cloudflare Turnstile
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
