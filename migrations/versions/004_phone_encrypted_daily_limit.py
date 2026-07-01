"""Add encrypted phone and daily publish log

Revision ID: 004_phone_encrypted_daily_limit
"""

import sqlalchemy as sa
from alembic import op

revision = "004_phone_encrypted_daily_limit"
down_revision = "003_post_slug"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phone_encrypted", sa.Text(), nullable=True))

    op.create_table(
        "phone_daily_publishes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("publish_date", sa.Date(), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_hash", "publish_date", name="uq_phone_daily_publish"),
    )
    op.create_index("ix_phone_daily_publishes_phone_hash", "phone_daily_publishes", ["phone_hash"])


def downgrade():
    op.drop_index("ix_phone_daily_publishes_phone_hash", table_name="phone_daily_publishes")
    op.drop_table("phone_daily_publishes")
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("phone_encrypted")
