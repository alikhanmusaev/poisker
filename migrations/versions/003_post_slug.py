"""Add slug to posts

Revision ID: 003_post_slug
"""

import sqlalchemy as sa
from alembic import op

revision = "003_post_slug"
down_revision = "002_seller_name"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=120), nullable=True))
        batch_op.create_index("ix_posts_slug", ["slug"], unique=True)


def downgrade():
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_index("ix_posts_slug")
        batch_op.drop_column("slug")
