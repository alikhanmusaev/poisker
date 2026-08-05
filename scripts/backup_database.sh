#!/usr/bin/env bash
set -euo pipefail

cd /opt/poisker
backup_dir="/opt/poisker/backups/database"
mkdir -p "$backup_dir"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$backup_dir/poisker-$stamp.sql.gz"

docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.server.yml \
  exec -T postgres pg_dump -U "${POSTGRES_USER:-board}" "${POSTGRES_DB:-chechnya_board}" \
  | gzip -9 > "$target"

test -s "$target"
find "$backup_dir" -type f -name 'poisker-*.sql.gz' -mtime +14 -delete
printf '%s database backup completed: %s\n' "$(date -u +%FT%TZ)" "$target"
