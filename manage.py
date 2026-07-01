"""CLI utilities for database setup."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from generate_icons import generate as generate_icons
from app import create_app
from app.extensions import db
from app.models import AdminUser
from app.services.search import get_index, reindex_published_posts
from app.services.seed import is_seeded, refresh_seed_images, seed_demo_posts
from app.services.storage import ensure_bucket
from sqlalchemy import inspect, text


def _ensure_schema():
    inspector = inspect(db.engine)
    if "posts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "seller_name" not in columns:
        db.session.execute(
            text("ALTER TABLE posts ADD COLUMN seller_name VARCHAR(80) NOT NULL DEFAULT ''")
        )
        db.session.commit()
    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "slug" not in columns:
        db.session.execute(text("ALTER TABLE posts ADD COLUMN slug VARCHAR(120)"))
        db.session.commit()

    from app.models import Post
    from app.services.slug import make_unique_slug

    missing = Post.query.filter((Post.slug.is_(None)) | (Post.slug == "")).all()
    if missing:
        for post in missing:
            post.slug = make_unique_slug(post.title, post.id)
        db.session.commit()
        print(f"Post slugs backfilled: {len(missing)}")


def init_db(seed: bool = True, force_seed: bool = False):
    generate_icons()
    app = create_app()
    with app.app_context():
        db.create_all()
        _ensure_schema()
        try:
            ensure_bucket()
            print("Storage bucket ready")
        except Exception as e:
            print(f"Storage warning: {e}")
        try:
            get_index()
            print("Typesense collection ready")
        except Exception as e:
            print(f"Typesense warning: {e}")

        production = os.getenv("FLASK_ENV", "development") == "production"
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "")
        if production and password in ("", "admin123", "password", "change-me"):
            raise RuntimeError("Production requires a strong ADMIN_PASSWORD")
        if not password:
            password = "admin123"
        if not AdminUser.query.filter_by(username=username).first():
            admin = AdminUser(username=username)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created: {username}")

        if seed:
            count = seed_demo_posts(force=force_seed)
            if count:
                print(f"Demo posts created: {count}")
            else:
                added = refresh_seed_images()
                if added:
                    print(f"Demo images added: {added}")
                elif is_seeded():
                    print("Demo posts already exist (skip)")
            reindexed = reindex_published_posts()
            if reindexed:
                print(f"Published posts indexed: {reindexed}")

        print("Database initialized")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "seed":
        app = create_app()
        with app.app_context():
            db.create_all()
            try:
                get_index()
            except Exception:
                pass
            force = "--force" in sys.argv
            count = seed_demo_posts(force=force)
            print(f"Demo posts: {count} created")
    elif cmd == "init":
        force_seed = os.getenv("SEED_FORCE", "").lower() in ("1", "true", "yes")
        production = os.getenv("FLASK_ENV", "development") == "production"
        seed_default = not production
        if "--seed" in sys.argv:
            seed = True
        elif "--no-seed" in sys.argv:
            seed = False
        else:
            seed = os.getenv("SEED_DEMO_DATA", "1" if seed_default else "0").lower() in (
                "1",
                "true",
                "yes",
            )
        init_db(seed=seed, force_seed=force_seed)
    else:
        print("Usage: python manage.py [init|seed] [--seed|--no-seed] [--force]")
        sys.exit(1)
