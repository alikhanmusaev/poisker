#!/usr/bin/env python
"""Background scheduler for Poisker Django."""

import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings

from listings.services.cleanup import cleanup_deleted_posts
from listings.services.ranking import expire_old_posts, recalculate_all_rank_scores
from listings.services.search import reindex_published_posts, upsert_published_rank_scores
from reviews.services import process_deal_review_jobs

scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)


@scheduler.scheduled_job("interval", minutes=30, id="recalc_ranks")
def recalc_job():
    recalculate_all_rank_scores()
    upsert_published_rank_scores()


@scheduler.scheduled_job("interval", hours=1, id="expire_posts")
def expire_job():
    expire_old_posts()


@scheduler.scheduled_job("interval", hours=6, id="listing_expiring_push")
def listing_expiring_push_job():
    from notifications.services import notify_listing_expiring

    notify_listing_expiring(days=3)


@scheduler.scheduled_job("interval", hours=1, id="deal_review_jobs")
def deal_review_job():
    process_deal_review_jobs()


@scheduler.scheduled_job("cron", hour=3, id="reindex_all")
def reindex_job():
    reindex_published_posts()


@scheduler.scheduled_job("cron", hour=3, minute=30, id="cleanup_deleted")
def cleanup_job():
    cleanup_deleted_posts()


if __name__ == "__main__":
    print("Starting Poisker scheduler...")
    scheduler.start()
