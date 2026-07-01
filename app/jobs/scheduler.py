from apscheduler.schedulers.background import BackgroundScheduler

from app.services.ranking import expire_old_posts, recalculate_all_rank_scores
from app.services.search import reindex_published_posts, upsert_published_rank_scores


scheduler = BackgroundScheduler()


def init_scheduler(app):
    if scheduler.running:
        return

    @scheduler.scheduled_job("interval", minutes=30, id="recalc_ranks")
    def recalc_job():
        with app.app_context():
            recalculate_all_rank_scores()
            try:
                upsert_published_rank_scores()
            except Exception:
                app.logger.exception("Scheduler: failed to upsert published rank scores")

    @scheduler.scheduled_job("interval", hours=1, id="expire_posts")
    def expire_job():
        with app.app_context():
            expire_old_posts()

    @scheduler.scheduled_job("cron", hour=3, id="reindex_all")
    def reindex_job():
        with app.app_context():
            try:
                reindex_published_posts()
            except Exception:
                app.logger.exception("Scheduler: failed to reindex published posts")

    scheduler.start()
