# Поискер — доска объявлений (poisker.ru)

Региональная доска объявлений для **Чеченской Республики**.

## Стек

- **Django 5** + PostgreSQL
- **HTMX** + Django templates
- Typesense, Redis, MinIO

## Аутентификация

Публикация объявлений только для зарегистрированных пользователей:

- Регистрация → `/accounts/register/`
- Вход → `/accounts/login/`
- Мои объявления → `/posts/my/`
- Профиль → `/accounts/profile/`

## Быстрый старт (Podman / Docker)

```bash
cp .env.example .env
./scripts/podman-up.sh
# или: docker compose build web && docker compose up -d
```

Сайт: http://127.0.0.1:8080/ (nginx) или http://127.0.0.1:8000/

Админка Django: http://127.0.0.1:8000/admin/
- Email: `admin@example.com`
- Пароль: `admin123`

## Локальная разработка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=true USE_SQLITE=true
python manage.py migrate
python manage.py bootstrap
python manage.py seed_demo
python manage.py runserver
```

## Структура проекта

```
config/          — настройки Django
accounts/        — пользователи (email + имя + пароль)
listings/        — объявления, CRUD, поиск, S3
core/            — главная, SEO-URL, health
templates/       — шаблоны
static/          — CSS, JS, изображения
mobile/          — Flutter-клиент (REST API + FCM), package `ru.poisker.app`
android/         — legacy Kotlin WebView-оболочка (тот же package)
```

## Мобильное приложение (Flutter)

Активный клиент: [`mobile/`](mobile/) — Flutter + `/api/v1/` + FCM.

```bash
cd mobile && flutter pub get && flutter run
```

Подробности: [`mobile/README.md`](mobile/README.md). Legacy WebView: [`android/README.md`](android/README.md).

## Полезные команды

```bash
python manage.py bootstrap      # Typesense + MinIO + superuser
python manage.py seed_demo      # демо-объявления
python manage.py seed_demo --force
python run_scheduler.py         # фоновые задачи (expiry, reindex)
```
