#!/usr/bin/env bash
# Install backup + monitor cron jobs for production host.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="# poisker-ops"
BACKUP_CRON="0 3 * * * cd $ROOT && bash $ROOT/scripts/backup.sh >> $ROOT/backups/logs/backup-cron.log 2>&1"
MONITOR_CRON="*/5 * * * * cd $ROOT && bash $ROOT/scripts/monitor.sh >> $ROOT/backups/logs/monitor-cron.log 2>&1"

chmod +x "$ROOT/scripts/backup.sh" "$ROOT/scripts/monitor.sh" "$ROOT/scripts/verify-backup.sh" "$ROOT/scripts/lib/env.sh"

mkdir -p "$ROOT/backups/logs"

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$MARKER" | grep -v "$ROOT/scripts/backup.sh" | grep -v "$ROOT/scripts/monitor.sh" > "$TMP" || true
{
  cat "$TMP"
  echo "$BACKUP_CRON $MARKER"
  echo "$MONITOR_CRON $MARKER"
} | crontab -
rm -f "$TMP"

echo "Installed cron jobs:"
crontab -l | grep "$MARKER"
