"""Add pending_revision and cover_index to posts

Revision ID: 006_pending_revision_cover
"""

from alembic import op
import sqlalchemy as sa

revision = "006_pending_revision_cover"
down_revision = "005_admin_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("pending_revision", sa.JSON(), nullable=True))
    op.add_column("posts", sa.Column("cover_index", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("posts", "cover_index")
    op.drop_column("posts", "pending_revision")
