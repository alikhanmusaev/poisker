#!/usr/bin/env bash
# Verify latest PostgreSQL backup exists and is non-trivial.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
PG_DIR="$BACKUP_ROOT/postgres"
MINIO_LATEST="$BACKUP_ROOT/minio/latest"

latest="$(ls -1t "$PG_DIR"/poisker-*.dump 2>/dev/null | head -1 || true)"
if [[ -z "$latest" ]]; then
  echo "FAIL: no PostgreSQL dumps in $PG_DIR"
  exit 1
fi

size="$(wc -c < "$latest" | tr -d ' ')"
if [[ "$size" -lt 1024 ]]; then
  echo "FAIL: dump too small ($size bytes): $latest"
  exit 1
fi

echo "OK: PostgreSQL $(basename "$latest") — ${size} bytes"

if [[ -L "$MINIO_LATEST" || -d "$MINIO_LATEST" ]]; then
  files="$(find -L "$MINIO_LATEST" -type f 2>/dev/null | wc -l | tr -d ' ')"
  echo "OK: MinIO latest — ${files} files"
else
  echo "WARN: MinIO latest symlink missing ($MINIO_LATEST)"
fi
