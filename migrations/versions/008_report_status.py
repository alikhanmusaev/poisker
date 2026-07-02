"""Add status and reviewed_at to reports

Revision ID: 008_report_status
"""

from alembic import op
import sqlalchemy as sa

revision = "008_report_status"
down_revision = "007_soft_delete_timestamps"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "reports",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
    )
    op.add_column("reports", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_reports_status", "reports", ["status"], unique=False)
    op.alter_column("reports", "status", server_default=None)


def downgrade():
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_column("reports", "reviewed_at")
    op.drop_column("reports", "status")
