#!/usr/bin/env bash
set -euo pipefail

cd /opt/poisker
state_file="/opt/poisker/backups/monitor-health.state"
recipient="oitarho@gmail.com"
url="https://poisker.ru/health"

previous="$(cat "$state_file" 2>/dev/null || true)"
if curl -fsS --max-time 15 "$url" | grep -q '"status"'; then
  current="up"
else
  current="down"
fi

if [[ "$current" != "$previous" ]]; then
  if [[ "$current" == "down" ]]; then
    subject="Poisker: сайт недоступен"
    body="Мониторинг не получил корректный ответ от $url в $(date -u +%FT%TZ)."
  elif [[ "$previous" == "down" ]]; then
    subject="Poisker: сайт восстановлен"
    body="Мониторинг снова получил корректный ответ от $url в $(date -u +%FT%TZ)."
  fi
  if [[ -n "${subject:-}" ]]; then
    docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.server.yml \
      exec -T web python manage.py send_monitor_email "$recipient" "$subject" "$body"
  fi
fi

printf '%s' "$current" > "$state_file"
