"""Revision ID: 001_initial
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "blocked_phones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_hash"),
    )
    op.create_index("ix_blocked_phones_phone_hash", "blocked_phones", ["phone_hash"])
    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("city", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("phone_masked", sa.String(length=20), nullable=False),
        sa.Column("edit_token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("contact_clicks", sa.Integer(), nullable=False),
        sa.Column("reports_count", sa.Integer(), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("has_photo", sa.Boolean(), nullable=False),
        sa.Column("paid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_boost", sa.Float(), nullable=False),
        sa.Column("bumped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edit_token"),
    )
    op.create_index("ix_posts_category", "posts", ["category"])
    op.create_index("ix_posts_city", "posts", ["city"])
    op.create_index("ix_posts_city_category_rank", "posts", ["city", "category", "rank_score"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_edit_token", "posts", ["edit_token"])
    op.create_index("ix_posts_expires_at", "posts", ["expires_at"])
    op.create_index("ix_posts_phone_created", "posts", ["phone_hash", "created_at"])
    op.create_index("ix_posts_phone_hash", "posts", ["phone_hash"])
    op.create_index("ix_posts_rank_score", "posts", ["rank_score"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_status_expires", "posts", ["status", "expires_at"])
    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payment_ref", sa.String(length=100), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promotions_post_id", "promotions", ["post_id"])
    op.create_index("ix_promotions_status", "promotions", ["status"])
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_post_id", "reports", ["post_id"])


def downgrade():
    op.drop_table("reports")
    op.drop_table("promotions")
    op.drop_table("posts")
    op.drop_table("blocked_phones")
    op.drop_table("admin_users")
