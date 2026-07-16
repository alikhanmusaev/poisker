#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NETWORK=poisker_net
POSTGRES_USER=board
POSTGRES_PASSWORD=board
POSTGRES_DB=chechnya_board
TYPESENSE_API_KEY=typesenseKey
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

podman network exists "$NETWORK" >/dev/null 2>&1 || podman network create "$NETWORK"
podman volume exists postgres_data >/dev/null 2>&1 || podman volume create postgres_data
podman volume exists typesense_data >/dev/null 2>&1 || podman volume create typesense_data
podman volume exists minio_data >/dev/null 2>&1 || podman volume create minio_data

start_if_missing() {
  local name=$1
  shift
  if podman container exists "$name" 2>/dev/null; then
    podman start "$name" >/dev/null
  else
    podman run -d --name "$name" "$@"
  fi
}

start_if_missing postgres \
  --network "$NETWORK" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -v postgres_data:/var/lib/postgresql/data \
  --health-cmd="pg_isready -U $POSTGRES_USER -d $POSTGRES_DB" \
  --health-interval=3s \
  --health-timeout=5s \
  --health-retries=10 \
  docker.io/postgres:16-alpine

start_if_missing redis \
  --network "$NETWORK" \
  --health-cmd="redis-cli ping" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  docker.io/redis:7.4.2-alpine

start_if_missing typesense \
  --network "$NETWORK" \
  -v typesense_data:/data \
  docker.io/typesense/typesense:26.0 \
  --data-dir /data --api-key="$TYPESENSE_API_KEY" --enable-cors

start_if_missing minio \
  --network "$NETWORK" \
  -e MINIO_ROOT_USER="$S3_ACCESS_KEY" \
  -e MINIO_ROOT_PASSWORD="$S3_SECRET_KEY" \
  -v minio_data:/data \
  docker.io/minio/minio:RELEASE.2025-04-22T22-12-26Z \
  server /data --console-address ":9001"

echo "Waiting for PostgreSQL..."
for _ in $(seq 1 60); do
  if podman exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Building web image..."
podman build -t poisker-web "$ROOT"

WEB_ENV=(
  -e DJANGO_DEBUG=true
  -e SECRET_KEY=dev-secret-key
  -e HMAC_SECRET=dev-hmac-secret
  -e PHONE_ENCRYPTION_KEY=dev-phone-encryption-key
  -e ADMIN_USERNAME=admin
  -e ADMIN_PASSWORD=admin123
  -e DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
  -e TYPESENSE_URL=http://typesense:8108
  -e TYPESENSE_API_KEY="$TYPESENSE_API_KEY"
  -e REDIS_URL=redis://redis:6379/0
  -e S3_ENDPOINT=http://minio:9000
  -e S3_PUBLIC_URL=http://localhost:9000/board-images
  -e S3_ACCESS_KEY="$S3_ACCESS_KEY"
  -e S3_SECRET_KEY="$S3_SECRET_KEY"
  -e RATELIMIT_STORAGE_URI=redis://redis:6379/1
  -e SCHEDULER_ENABLED=false
  -e SESSION_COOKIE_SECURE=false
  -e REQUIRE_CAPTCHA=false
  -e CAPTCHA_PROVIDER=builtin
  -e TRUST_PROXY=true
  -e HSTS_ENABLED=false
  -e RUN_DB_UPGRADE=true
  -e RUN_DB_INIT=false
  -e WEB_CONCURRENCY=2
  -e SEED_DEMO_DATA=1
)

if podman container exists web 2>/dev/null; then
  podman rm -f web >/dev/null
fi

podman run -d --name web \
  --network "$NETWORK" \
  -p 127.0.0.1:8000:8000 \
  "${WEB_ENV[@]}" \
  poisker-web

SCHEDULER_ENV=(
  -e DJANGO_DEBUG=true
  -e SECRET_KEY=dev-secret-key
  -e HMAC_SECRET=dev-hmac-secret
  -e PHONE_ENCRYPTION_KEY=dev-phone-encryption-key
  -e DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
  -e TYPESENSE_URL=http://typesense:8108
  -e TYPESENSE_API_KEY="$TYPESENSE_API_KEY"
  -e REDIS_URL=redis://redis:6379/0
  -e S3_ENDPOINT=http://minio:9000
  -e S3_PUBLIC_URL=http://localhost:9000/board-images
  -e S3_ACCESS_KEY="$S3_ACCESS_KEY"
  -e S3_SECRET_KEY="$S3_SECRET_KEY"
  -e SCHEDULER_ENABLED=true
)

if podman container exists scheduler 2>/dev/null; then
  podman rm -f scheduler >/dev/null
fi

podman run -d --name scheduler \
  --network "$NETWORK" \
  --entrypoint ./scheduler_entrypoint.sh \
  "${SCHEDULER_ENV[@]}" \
  poisker-web

if podman container exists nginx 2>/dev/null; then
  podman rm -f nginx >/dev/null
fi

podman run -d --name nginx \
  --network "$NETWORK" \
  -p 127.0.0.1:8080:80 \
  -v "$ROOT/nginx.conf:/etc/nginx/conf.d/default.conf:ro,Z" \
  -v "$ROOT/static:/app/static:ro,z" \
  docker.io/nginx:1.27-alpine

echo "Waiting for web..."
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/ready >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

podman restart nginx >/dev/null 2>&1 || true

echo
echo "Poisker is up:"
echo "  http://127.0.0.1:8080/   (nginx)"
echo "  http://127.0.0.1:8000/   (web direct)"
echo "  http://127.0.0.1/admin   admin / admin123"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
