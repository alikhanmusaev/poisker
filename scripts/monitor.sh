#!/usr/bin/env bash
# Health monitor: HTTP /health, Docker services, disk space.
# Optional Telegram alerts via MONITOR_TELEGRAM_* in .env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/env.sh"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
STATE_FILE="${MONITOR_STATE_FILE:-$ROOT/backups/.monitor-state}"
LOG_DIR="$ROOT/backups/logs"
ALERT_INTERVAL="${MONITOR_ALERT_INTERVAL_SEC:-1800}"
DISK_WARN_PCT="${MONITOR_DISK_WARN_PCT:-85}"

mkdir -p "$LOG_DIR"

MONITOR_TELEGRAM_BOT_TOKEN=""
MONITOR_TELEGRAM_CHAT_ID=""
APP_DOMAIN="poisker.ru"
URL="${MONITOR_URL:-https://poisker.ru/health}"

if [[ -f "$ROOT/.env" ]]; then
  MONITOR_TELEGRAM_BOT_TOKEN="$(get_env MONITOR_TELEGRAM_BOT_TOKEN)"
  MONITOR_TELEGRAM_CHAT_ID="$(get_env MONITOR_TELEGRAM_CHAT_ID)"
  APP_DOMAIN="$(get_env APP_DOMAIN poisker.ru)"
  env_url="$(get_env MONITOR_URL)"
  if [[ -n "$env_url" ]]; then
    URL="$env_url"
  fi
fi
if [[ -n "${MONITOR_URL:-}" ]]; then
  URL="$MONITOR_URL"
fi

send_alert() {
  local msg="$1"
  local ts
  ts="$(date -Iseconds)"
  echo "[$ts] ALERT: $msg" >> "$LOG_DIR/monitor.log"

  if [[ -n "${MONITOR_TELEGRAM_BOT_TOKEN:-}" && -n "${MONITOR_TELEGRAM_CHAT_ID:-}" ]]; then
    curl -sf -m 15 -X POST \
      "https://api.telegram.org/bot${MONITOR_TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${MONITOR_TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=Poisker ${APP_DOMAIN:-poisker.ru}: ${msg}" >/dev/null || true
  fi
}

should_alert() {
  local now last
  now="$(date +%s)"
  last="0"
  if [[ -f "$STATE_FILE" ]]; then
    last="$(grep '^last_alert=' "$STATE_FILE" 2>/dev/null | cut -d= -f2 || echo 0)"
  fi
  if (( now - last >= ALERT_INTERVAL )); then
    return 0
  fi
  return 1
}

mark_alert() {
  local status="$1"
  mkdir -p "$(dirname "$STATE_FILE")"
  cat > "$STATE_FILE" <<EOF
status=$status
last_alert=$(date +%s)
last_check=$(date -Iseconds)
EOF
}

mark_ok() {
  local prev=""
  if [[ -f "$STATE_FILE" ]]; then
    prev="$(grep '^status=' "$STATE_FILE" 2>/dev/null | cut -d= -f2 || true)"
  fi
  mark_alert "ok"
  if [[ "$prev" == "fail" ]]; then
    send_alert "восстановлен после сбоя"
  fi
}

fail() {
  local reason="$1"
  if should_alert; then
    send_alert "$reason"
    mark_alert "fail"
  else
    echo "[$(date -Iseconds)] still failing: $reason" >> "$LOG_DIR/monitor.log"
  fi
  exit 1
}

# HTTP health
HTTP_CODE="$(curl -sf -m 20 -o /dev/null -w '%{http_code}' "$URL" || echo 000)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "health check failed (HTTP $HTTP_CODE) $URL"
fi

# Docker services
UNHEALTHY="$("${COMPOSE[@]}" ps --format '{{.Service}}:{{.Health}}' 2>/dev/null | grep -v healthy | grep -v ':$' || true)"
if [[ -n "$UNHEALTHY" ]]; then
  fail "unhealthy containers: $(echo "$UNHEALTHY" | tr '\n' ' ')"
fi

STOPPED="$("${COMPOSE[@]}" ps --format '{{.Service}}:{{.State}}' 2>/dev/null | grep -v running | grep -v ':$' || true)"
if [[ -n "$STOPPED" ]]; then
  fail "stopped containers: $(echo "$STOPPED" | tr '\n' ' ')"
fi

# Disk space
DISK_USE="$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')"
if [[ "$DISK_USE" -ge "$DISK_WARN_PCT" ]]; then
  fail "disk usage ${DISK_USE}% (threshold ${DISK_WARN_PCT}%)"
fi

mark_ok
echo "[$(date -Iseconds)] OK health=$HTTP_CODE disk=${DISK_USE}%" >> "$LOG_DIR/monitor.log"
