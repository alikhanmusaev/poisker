# Poisker — план JSON API для Android

Документ основан на анализе реального Django-проекта (`main`, июль 2026).  
Цель: нативный Android-клиент без WebView, без изменения HTML-маршрутов и без дублирования бизнес-логики.

---

## 1. Реальные модели

### `accounts.User` (`accounts/models.py`)

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | BigAutoField | PK |
| `email` | EmailField, unique | Логин (`USERNAME_FIELD`) |
| `display_name` | CharField(80) | Имя продавца |
| `phone` | CharField(20) | Телефон (нормализуется при save) |
| `phone_digits` | CharField(11), unique | Цифры телефона |
| `phone_verified` | Boolean | Пока не используется в UI |
| `email_verified` | Boolean | Обязателен для входа (кроме staff) |
| `terms_accepted_at` | DateTime | Согласие с условиями |
| `pdn_consent_at`, `pdn_consent_version`, `consent_ip` | | Согласие ПДн (152-ФЗ) |
| `is_blocked` | Boolean | Блокировка (middleware разлогинивает) |
| `rating_avg`, `rating_count` | Float/Int | Денормализация отзывов |
| `created_at` | DateTime | |
| `username` | — | **Отсутствует** |

### `listings.Post` (`listings/models.py`)

UUID PK. Ключевые поля:

- `title` (200), `body` (Text)
- `category`, `city` — slug из справочников (`listings/constants.py`)
- `condition` — `used` \| `new`
- `price` — PositiveInteger, nullable («по договорённости»)
- `contact_phone` — копия телефона продавца
- `status` — см. §3
- `images` — JSONField, список URL вида `/media/posts/{hex}.jpg`
- `cover_index` — индекс обложки
- `pending_revision` — JSON с правками опубликованного объявления (модерация)
- `moderation_note` — причина отклонения
- `views`, `contact_clicks`, `reports_count`
- `expires_at` — срок публикации (+30 дней по умолчанию)

### `bookmarks.PostBookmark`

`user` + `post`, unique together, `created_at`.

### `bookmarks.CategoryBookmark`

`user` + `category` slug, unique together.

### `bookmarks.Notification`

In-app уведомления (12 видов). Для Android MVP **не включать** — отдельный этап.

### `messaging.Conversation` / `Message`

Переписка по объявлению, deal confirmation, soft hide. Для Android MVP **не включать**.

### `reviews.SellerReview` / `PhoneReveal`

Отзывы после подтверждения сделки. Для Android MVP **не включать**.

### Справочники (не в БД)

- **Категории:** 17 slug → label + icon (`listings/constants.py` → `CATEGORIES`)
- **Города:** ~350 населённых пунктов Чечни (`listings/data/chechnya_settlements.py` → `CITIES`)
- **Регионы:** **отсутствуют** в проекте. Фильтр `region` в API не реализовывать.

---

## 2. Текущая авторизация (веб)

| Механизм | Реализация |
|----------|------------|
| Backend | `accounts.backends.EmailBackend` — вход по email + password |
| Сессия | Django session cookie, `SESSION_COOKIE_HTTPONLY=True` |
| Регистрация | `RegistrationForm`: display_name, email, phone, password, accept_terms, accept_pdn |
| Верификация email | `EmailVerificationTokenGenerator`, `email_verified=False` до подтверждения |
| Блокировка входа | `LoginForm.clean()`: не-staff без `email_verified` → ошибка |
| Телефон | `core.phone.ensure_phone_available`, уникальность `phone_digits` |
| API-токены | **Отсутствуют** |

### Рекомендация для Android

**JWT через `djangorestframework-simplejwt`:**

- Access token: 15–30 мин (в памяти приложения)
- Refresh token: 7–30 дней (blacklist при logout через `rest_framework_simplejwt.token_blacklist`)
- Кастомный claim: `email`, `display_name` (опционально)
- Аутентификация по `email` + `password` — совместима с `User.USERNAME_FIELD = "email"`
- Веб продолжает использовать session auth; API — только JWT (`Authorization: Bearer`)

Регистрация через API должна вызывать ту же валидацию, что `RegistrationForm` + `UserManager.create_user`, и отправлять verification email (`accounts/services/email.py`).

---

## 3. Статусы объявления

```
draft → pending → published → expired
                  ↓     ↑
                hidden ─┘ (republish → pending)
                  ↓
               deleted (только если never published)
```

| Статус | Публично в ленте | Описание |
|--------|------------------|----------|
| `draft` | Нет | Черновик автора |
| `pending` | Нет | На модерации |
| `published` | Да (если `expires_at > now`) | Опубликовано |
| `hidden` | Нет | Снято / отклонено |
| `expired` | Нет | Истёк срок |
| `deleted` | Нет | Мягкое удаление |

### Переходы (через `listings/services/posts.py`)

| Действие | Сервис | API-аналог |
|----------|--------|------------|
| Создать | `create_post(as_draft=False)` | `POST /listings/` → `pending` |
| Черновик | `create_post(as_draft=True)` | `POST /listings/` + `?as_draft=1` или поле `as_draft` |
| Отправить черновик | `submit_draft` | `POST /listings/{uuid}/submit/` |
| Редактировать | `update_post` | `PATCH /listings/{uuid}/` |
| Снять с публикации | `unpublish_post` | `DELETE` или `POST .../unpublish/` |
| Удалить | `delete_post` | `DELETE` (только never published) |
| Повторная публикация | `republish_post` | `POST /listings/{uuid}/republish/` |
| Одобрить/отклонить | `moderation/services.py` | Только staff (вне Android MVP) |

**`mark-sold` не существует** в backend. Не добавлять endpoint. Для «продано» использовать `unpublish_post` (статус `hidden`).

---

## 4. Категории и города

### Категории (17)

`nedvizhimost`, `avto`, `zapchasti`, `elektronika`, `odezhda`, `prodazha`, `dlya-doma`, `uslugi`, `rabota`, `detskie`, `zhivotnye`, `sport`, `stroitelstvo`, `rasteniya`, `produkti`, `biznes`, `drugoe`.

### Города (~350)

Плоский словарь slug → русское название. Без иерархии регионов.

### Поиск и фильтрация (реально используется в `core/views.py` + `listings/services/search.py`)

| Параметр | Имя в API | Примечание |
|----------|-----------|------------|
| Текст | `search` | Аналог `q` |
| Категория | `category` | slug |
| Город | `city` | slug |
| Цена от/до | `min_price`, `max_price` | int |
| Сортировка | `ordering` | `rank`, `relevance`, `date_desc`, `price_asc`, `price_desc` |
| Страница | `page` | 20 элементов (`PER_PAGE`) |
| Регион | — | **Не реализовывать** |

Публичный список: только `status=published` и `expires_at >= now` (логика в `search_posts` / Typesense).

---

## 5. Фотографии

| Ограничение | Значение |
|-------------|----------|
| Макс. файлов | 5 |
| Макс. размер | 20 МБ (`MAX_UPLOAD_SIZE`) |
| Форматы | jpg, jpeg, png, webp |
| Хранение | MinIO/S3, ключ `posts/{uuid}.jpg` |
| URL в модели | `/media/posts/{uuid}.jpg` (относительный) |
| Обработка | `listings/services/storage.upload_image` — canonical JPEG + фоновые WebP/thumb |
| Порядок | Порядок в JSON-массиве `images` + `cover_index` |

### API загрузки

- `multipart/form-data` при создании/редактировании
- Поля: `images[]` (файлы), `cover_index` (int)
- При редактировании: `remove_images[]` (индексы), новые файлы добавляются
- Переиспользовать `_upload_images` / `upload_image` из существующего кода
- В ответе API — **абсолютные HTTPS URL**: `https://poisker.ru/media/posts/...` (через `APP_DOMAIN`)

Base64 не использовать.

---

## 6. Bookmarks

Модель: `bookmarks.PostBookmark`.

| Веб | Поведение |
|-----|-----------|
| `POST /bookmarks/posts/<uuid>/toggle/` | Идемпотентный toggle, JSON `{ok, bookmarked}` |

Сервис: `bookmarks.services.toggle_post_bookmark`.

### API

```
GET    /api/v1/me/bookmarks/
POST   /api/v1/listings/{uuid}/bookmark/      → добавить (201 или 200)
DELETE /api/v1/listings/{uuid}/bookmark/      → убрать (204)
```

Повторный POST не создаёт дубликат (unique constraint + try/except в сервисе).

`CategoryBookmark` — опционально во второй итерации; в Android MVP достаточно post bookmarks.

---

## 7. Messaging (этап 2)

Модели готовы (`Conversation`, `Message`), сервисы в `messaging/services.py`.

Сложности для MVP:

- Deal confirmation ↔ reviews
- Per-user soft hide
- Rate limit 60 msg/hour
- Нет WebSocket/push

**Решение:** не включать в Android MVP и backend API v1 messaging endpoints до завершения listings MVP.

Минимальный задел: `POST /api/v1/listings/{uuid}/contact/` — аналог существующего JSON `POST /posts/{uuid}/contact/` (возврат телефона, rate limit).

---

## 8. Reviews (этап 2)

`reviews.SellerReview`, eligibility через deal confirmation. Отложить.

---

## 9. Зависимости (добавить в `requirements.txt`)

```
djangorestframework>=3.15,<4
djangorestframework-simplejwt>=5.3,<6
drf-spectacular>=0.27,<1
```

Опционально: `django-cors-headers` — только если понадобится CORS (для нативного Android обычно не нужен).

---

## 10. Изменения в `config/settings.py`

```python
INSTALLED_APPS += [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "api",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.PoiskerPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.poisker_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Poisker API",
    "VERSION": "1.0.0",
}
```

В `DEBUG=True` добавить `/api/schema/`, `/api/docs/`.

---

## 11. Структура приложения `api/`

```
api/
  __init__.py
  apps.py
  urls.py
  permissions.py          # IsOwner, not blocked
  pagination.py           # count/next/previous/results
  exceptions.py           # единый формат ошибок
  authentication.py       # (опционально) blocked user check

  serializers/
    auth.py
    category.py
    location.py
    listing.py
    user.py
    bookmark.py

  views/
    auth.py
    categories.py
    locations.py
    listings.py
    bookmarks.py
    profile.py
```

`config/urls.py`:

```python
path("api/v1/", include("api.urls")),
```

---

## 12. Endpoints

### Auth

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| POST | `/api/v1/auth/register/` | — | Как `RegistrationForm` |
| POST | `/api/v1/auth/login/` | — | email + password → tokens |
| POST | `/api/v1/auth/refresh/` | refresh | Новый access |
| POST | `/api/v1/auth/logout/` | refresh | Blacklist refresh |
| GET | `/api/v1/auth/me/` | JWT | Профиль |

### Справочники

| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/categories/` | 17 категорий: slug, label, icon |
| GET | `/api/v1/cities/` | Список городов; `?search=` фильтр по названию |

`/api/v1/regions/` — **не реализовывать** (нет данных в backend).

### Listings (публичные)

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| GET | `/api/v1/listings/` | — | Поиск/лента (`search_posts`) |
| GET | `/api/v1/listings/{uuid}/` | — | Карточка (только published+live для чужих) |
| POST | `/api/v1/listings/{uuid}/contact/` | JWT | Телефон продавца (rate limit) |
| POST | `/api/v1/listings/{uuid}/report/` | JWT | Жалоба (опционально MVP+) |

### Listings (владелец)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/me/listings/` | Все свои объявления |
| POST | `/api/v1/listings/` | Создать (multipart) |
| PATCH | `/api/v1/listings/{uuid}/` | Редактировать (multipart) |
| DELETE | `/api/v1/listings/{uuid}/` | Удалить или снять |
| POST | `/api/v1/listings/{uuid}/submit/` | Черновик → модерация |
| POST | `/api/v1/listings/{uuid}/republish/` | hidden/expired → pending |

### Bookmarks

| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/me/bookmarks/` | Список избранных |
| POST | `/api/v1/listings/{uuid}/bookmark/` | Добавить |
| DELETE | `/api/v1/listings/{uuid}/bookmark/` | Удалить |

### Profile

| Method | Path | Описание |
|--------|------|----------|
| PATCH | `/api/v1/me/profile/` | display_name, phone |

---

## 13. Формат ответов

### Пагинация

```json
{
  "count": 120,
  "next": "https://poisker.ru/api/v1/listings/?page=2",
  "previous": null,
  "results": []
}
```

### Listing (пример)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "iPhone 13",
  "body": "...",
  "category": "elektronika",
  "category_label": "Электроника",
  "city": "grozny",
  "city_label": "Грозный",
  "condition": "used",
  "price": 45000,
  "price_display": "45 000 ₽",
  "status": "published",
  "images": [
    "https://poisker.ru/media/posts/abc.jpg"
  ],
  "cover_index": 0,
  "has_photo": true,
  "views": 42,
  "created_at": "2026-07-01T10:00:00+03:00",
  "expires_at": "2026-07-31T10:00:00+03:00",
  "public_url": "https://poisker.ru/obyavlenie/grozny/elektronika/...",
  "seller": {
    "id": 1,
    "display_name": "Али",
    "rating_avg": 4.8,
    "rating_count": 12
  },
  "is_bookmarked": false
}
```

### Ошибки

```json
{
  "code": "validation_error",
  "message": "Проверьте введённые данные",
  "fields": {
    "title": ["Заголовок: от 5 до 50 символов."]
  }
}
```

Коды: `validation_error`, `authentication_failed`, `permission_denied`, `not_found`, `rate_limited`, `server_error`.

---

## 14. Serializers (кратко)

| Serializer | Источник данных |
|------------|-----------------|
| `UserSerializer` | `accounts.User` |
| `RegisterSerializer` | `RegistrationForm` rules |
| `CategorySerializer` | `CATEGORIES` dict |
| `CitySerializer` | `CITIES` dict |
| `ListingListSerializer` | `Post` + labels + cover image |
| `ListingDetailSerializer` | + seller, phone_masked, is_owner |
| `ListingWriteSerializer` | → `create_post` / `update_post` |
| `BookmarkSerializer` | `PostBookmark` + nested listing |

---

## 15. Permissions

| Правило | Реализация |
|---------|------------|
| Публичное чтение | `published` + not expired |
| Редактирование | `post.user_id == request.user.id` |
| Заблокированный | `api.permissions.NotBlocked` → 403 |
| Staff moderation | Не в Android API |

---

## 16. Тесты backend (`tests/test_api/`)

- [ ] register / login / refresh / logout / me
- [ ] публичный список только published
- [ ] деталь объявления
- [ ] create / update own / forbidden other user
- [ ] submit draft / republish
- [ ] delete vs unpublish rules
- [ ] bookmarks add/remove/list
- [ ] pagination count/next
- [ ] filters: category, city, price, search
- [ ] multipart image upload (mock S3)
- [ ] moderation: pending after create
- [ ] contact rate limit
- [ ] error format

Существующие тесты не трогать.

---

## 17. OpenAPI

`drf-spectacular`:

- `GET /api/schema/` — OpenAPI 3
- `GET /api/docs/` — Swagger UI (только `DEBUG=True`)

---

## 18. Файлы backend для изменения

| Файл | Изменение |
|------|-----------|
| `requirements.txt` | DRF, SimpleJWT, spectacular |
| `config/settings.py` | REST_FRAMEWORK, SIMPLE_JWT, INSTALLED_APPS |
| `config/urls.py` | `path("api/v1/", ...)` |
| `api/` | Новое приложение (см. §11) |
| `tests/test_api/` | Новые тесты |

**Не менять:** `listings/views.py`, HTML templates, HTMX routes, `moderation/`, business logic в `services/`.

---

## 19. План Android MVP (этап 3)

После готовности API и прохождения тестов.

### Стек

- Kotlin, Jetpack Compose, Material 3
- package: `ru.poisker.app`, minSdk 24
- Hilt, Retrofit, OkHttp, Kotlin Serialization, Coil, DataStore, Navigation Compose

### Base URL

- Release: `https://poisker.ru/api/v1/`
- Debug: `BuildConfig.API_BASE_URL` (default `http://10.0.2.2:8000/api/v1/`)
- Cleartext только в `debug` manifest для `10.0.2.2`

### Архитектура (один модуль `app/`)

```
app/src/main/java/ru/poisker/app/
  data/remote/       # Retrofit API, DTO, AuthInterceptor
  data/repository/
  domain/model/
  domain/repository/
  ui/theme/          # PoiskerColors, Typography, Spacing из CSS
  ui/components/     # PostCard, PriceTag, CityChip, ...
  ui/navigation/
  ui/screens/
    home/
    details/
    create/
    my/
    auth/
    bookmarks/
```

### Design system (из `static/css/style.css`)

| Token | Значение |
|-------|----------|
| Primary | `#b91c1c` |
| Primary hover | `#dc2626` |
| Background | `#f8fafc` |
| Surface | `#ffffff` |
| Text | `#0f172a` |
| Muted | `#64748b` |
| Border | `#e2e8f0` |
| Radius sm/md/lg | 8 / 12 / 16 dp |
| Font | Inter (уже в static/fonts/inter) |

Dynamic Color: **выключен**.

### Экраны MVP

1. Главная (лента, поиск, категории, город, сортировка, pull-to-refresh, пагинация)
2. Карточка объявления (галерея, цена, описание, звонок через `ACTION_DIAL`, избранное, share, report)
3. Регистрация / вход / выход
4. Мои объявления (все статусы)
5. Создание / редактирование (multipart, photo picker, cover, валидация)
6. Избранное

### Нижнее меню

- Главная | Подать | Мои (избранное из «Мои» или top bar)

### Не в MVP

- Сообщения, отзывы, уведомления, category bookmarks

### Токены

- Access — в памяти
- Refresh — Encrypted DataStore / EncryptedSharedPreferences
- OkHttp interceptor: Bearer, refresh on 401, logout on refresh fail

---

## 20. Порядок реализации

### Этап 2a — Backend skeleton

1. Зависимости + `api` app + settings
2. Auth endpoints + tests
3. Categories/cities read-only
4. Listings read (public)
5. Listings write (owner) + images
6. Bookmarks + contact
7. OpenAPI + полный test suite

### Этап 2b — Проверка

```bash
python manage.py check
python manage.py test
```

### Этап 3 — Android

1. Gradle project `android/` (Compose, Hilt)
2. Theme + navigation shell
3. Auth flow
4. Home + listings
5. Details + bookmarks
6. Create/edit + image upload
7. `./gradlew assembleDebug test lint`

---

## 21. Риски и ограничения

| Риск | Митигация |
|------|-----------|
| Нет регионов | Города плоским списком + search |
| Нет mark-sold | Документировать `hidden` через unpublish |
| Email verification блокирует login | Android показывает экран «подтвердите email» |
| Модерация обязательна | Статус `pending` после создания — UI должен объяснять |
| Typesense down | `search_posts` fallback на ORM |
| S3 upload slow | Клиентское сжатие (уже на вебе) + фоновые variants |

---

*Документ подготовлен по состоянию репозитория на ветке `main`. Следующий шаг: реализация этапа 2 (Django REST API) по этому плану.*
