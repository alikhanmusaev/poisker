"""Add admin audit logs

Revision ID: 005_admin_audit_logs
"""

import sqlalchemy as sa
from alembic import op

revision = "005_admin_audit_logs"
down_revision = "004_phone_encrypted_daily_limit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
