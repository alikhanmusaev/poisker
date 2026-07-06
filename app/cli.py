import click

from flask import Flask


def register_cli(app: Flask) -> None:
    @app.cli.command("cleanup-deleted-posts")
    @click.option("--days", type=int, default=None, help="Retention days override")
    @click.option("--batch-size", type=int, default=None, help="Batch size override")
    def cleanup_deleted_posts_cmd(days, batch_size):
        """Remove images and encrypted phones from deleted posts past retention."""
        from app.services.cleanup import cleanup_deleted_posts

        stats = cleanup_deleted_posts(retention_days=days, batch_size=batch_size)
        click.echo(f"Processed: {stats['processed']}")
        click.echo(f"Images deleted: {stats['images_deleted']}")
        click.echo(f"Phones cleared: {stats['phone_encrypted_cleared']}")

    @app.cli.command("seed-demo-posts")
    @click.option("--force", is_flag=True, help="Replace existing demo posts")
    def seed_demo_posts_cmd(force):
        """Create demo listings for development and empty catalogs."""
        from app.services.search import reindex_published_posts
        from app.services.seed import seed_demo_posts

        count = seed_demo_posts(force=force)
        if count:
            click.echo(f"Demo posts created: {count}")
        else:
            click.echo("Demo posts already exist (use --force to recreate)")
        reindexed = reindex_published_posts()
        if reindexed:
            click.echo(f"Published posts indexed: {reindexed}")

    @app.cli.command("purge-all-posts")
    @click.option("--yes", is_flag=True, help="Confirm destructive purge")
    @click.option("--keep-daily-limits", is_flag=True, help="Keep phone_daily_publishes rows")
    def purge_all_posts_cmd(yes, keep_daily_limits):
        """Hard-delete all posts, uploaded images, and search index documents."""
        if not yes:
            raise click.ClickException("Refusing to purge without --yes")

        from app.services.purge import purge_all_posts

        stats = purge_all_posts(clear_daily_limits=not keep_daily_limits)
        click.echo(f"Posts deleted: {stats['posts_deleted']}")
        click.echo(f"Images deleted: {stats['images_deleted']}")
        click.echo(f"Orphan S3 objects deleted: {stats['orphan_objects_deleted']}")
        click.echo(f"Daily publish limits cleared: {stats['daily_limits_cleared']}")
