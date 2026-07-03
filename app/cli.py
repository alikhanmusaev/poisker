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
