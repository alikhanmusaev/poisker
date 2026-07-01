"""Dedicated scheduler process — run once per deployment, not per Gunicorn worker."""

import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.jobs.scheduler import init_scheduler, scheduler


def _wait_for_postgres():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        return

    import psycopg

    url = database_url.replace("postgresql+psycopg://", "postgresql://")
    for _ in range(30):
        try:
            psycopg.connect(url).close()
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("PostgreSQL not ready")


def main():
    _wait_for_postgres()
    app = create_app()
    with app.app_context():
        init_scheduler(app)
        app.logger.info("Scheduler started (pid %s)", os.getpid())

    def shutdown(signum, _frame):
        if scheduler.running:
            scheduler.shutdown(wait=False)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
