"""Add deleted_at and updated_at to posts

Revision ID: 007_soft_delete_timestamps
"""

from alembic import op
import sqlalchemy as sa

revision = "007_soft_delete_timestamps"
down_revision = "006_pending_revision_cover"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("posts", "updated_at")
    op.drop_column("posts", "deleted_at")
