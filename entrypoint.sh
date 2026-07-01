#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import os, time
import psycopg
url = os.environ.get('DATABASE_URL', '').replace('postgresql+psycopg://', 'postgresql://')
for i in range(30):
    try:
        psycopg.connect(url)
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('PostgreSQL not ready')
" 2>/dev/null; do
  sleep 1
done

if [ "${RUN_DB_UPGRADE:-false}" = "true" ]; then
  echo "Running database migrations..."
  flask db upgrade
  echo "Running post-migration bootstrap..."
  python manage.py bootstrap
elif [ "${RUN_DB_INIT:-false}" = "true" ]; then
  echo "Initializing database..."
  python manage.py init --no-seed
else
  echo "Skipping database migration/init (set RUN_DB_UPGRADE=true for migrations)."
fi

echo "Starting gunicorn..."
exec gunicorn -w "${WEB_CONCURRENCY:-2}" -b 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 wsgi:app
