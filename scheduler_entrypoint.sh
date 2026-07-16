#!/bin/sh
set -e
if [ "$(id -u)" = "0" ]; then
  exec gosu appuser "$0" "$@"
fi
echo "Starting Django scheduler..."
exec python run_scheduler.py
