#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/staticfiles /app/media
  chown -R appuser:appuser /app/staticfiles /app/media
  exec gosu appuser "$0" "$@"
fi

echo "Waiting for PostgreSQL..."
until python - <<'PY'
import os, time
import psycopg
url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    url = f"postgresql://{os.environ.get('POSTGRES_USER','board')}:{os.environ.get('POSTGRES_PASSWORD','board')}@postgres:5432/{os.environ.get('POSTGRES_DB','chechnya_board')}"
for _ in range(60):
    try:
        psycopg.connect(url)
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL not ready")
PY
do sleep 1; done

echo "Running migrations..."
python manage.py migrate --noinput
python manage.py bootstrap
if [ "${SEED_DEMO_DATA:-0}" = "1" ]; then
  python manage.py seed_demo
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application -w "${WEB_CONCURRENCY:-2}" -b 0.0.0.0:8000 --timeout 120
