"""Add seller_name to posts."""

from alembic import op
import sqlalchemy as sa

revision = "002_seller_name"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "posts",
        sa.Column("seller_name", sa.String(length=80), nullable=False, server_default=""),
    )
    op.alter_column("posts", "seller_name", server_default=None)


def downgrade():
    op.drop_column("posts", "seller_name")
