#!/usr/bin/env bash
# Daily backup: PostgreSQL dump + MinIO bucket mirror.
# Usage: ./scripts/backup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/env.sh"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
DATE="$(date +%Y%m%d)"
TS="$(date +%Y%m%d-%H%M)"
LOG_DIR="$BACKUP_ROOT/logs"
PG_DIR="$BACKUP_ROOT/postgres"
MINIO_DIR="$BACKUP_ROOT/minio/$DATE"
RETENTION_DB="${BACKUP_RETENTION_DAYS_DB:-14}"
RETENTION_MINIO="${BACKUP_RETENTION_DAYS_MINIO:-7}"

mkdir -p "$LOG_DIR" "$PG_DIR" "$MINIO_DIR"

log() {
  echo "[$(date -Iseconds)] $*"
}

if [[ ! -f "$ROOT/.env" ]]; then
  log "ERROR: .env not found in $ROOT"
  exit 1
fi

POSTGRES_USER="$(get_env POSTGRES_USER board)"
POSTGRES_DB="$(get_env POSTGRES_DB chechnya_board)"
S3_BUCKET="$(get_env S3_BUCKET board-images)"
S3_ENDPOINT="$(get_env S3_ENDPOINT http://minio:9000)"
S3_ACCESS_KEY="$(get_env S3_ACCESS_KEY)"
S3_SECRET_KEY="$(get_env S3_SECRET_KEY)"
DOCKER_NETWORK="${DOCKER_NETWORK:-poisker_default}"

PG_FILE="$PG_DIR/poisker-${TS}.dump"
log "PostgreSQL backup -> $PG_FILE"
"${COMPOSE[@]}" exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --format=custom \
  > "$PG_FILE"

PG_SIZE="$(wc -c < "$PG_FILE" | tr -d ' ')"
if [[ "$PG_SIZE" -lt 1024 ]]; then
  log "ERROR: PostgreSQL dump too small (${PG_SIZE} bytes)"
  exit 1
fi
log "PostgreSQL OK (${PG_SIZE} bytes)"

log "MinIO backup -> $MINIO_DIR"
docker run --rm \
  --network "$DOCKER_NETWORK" \
  --entrypoint /bin/sh \
  -v "$MINIO_DIR:/backup" \
  -e "S3_ENDPOINT=$S3_ENDPOINT" \
  -e "S3_ACCESS_KEY=$S3_ACCESS_KEY" \
  -e "S3_SECRET_KEY=$S3_SECRET_KEY" \
  -e "S3_BUCKET=$S3_BUCKET" \
  minio/mc:latest \
  -ec '
    mc alias set local "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null
    mc mirror --quiet "local/$S3_BUCKET" /backup
  '

FILE_COUNT="$(find "$MINIO_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')"
log "MinIO OK (${FILE_COUNT} files)"

log "Prune PostgreSQL backups older than ${RETENTION_DB} days"
find "$PG_DIR" -name 'poisker-*.dump' -mtime +"$RETENTION_DB" -delete 2>/dev/null || true

log "Prune MinIO backups older than ${RETENTION_MINIO} days"
find "$BACKUP_ROOT/minio" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_MINIO" -exec rm -rf {} + 2>/dev/null || true

ln -sfn "$MINIO_DIR" "$BACKUP_ROOT/minio/latest"
log "Backup complete"
