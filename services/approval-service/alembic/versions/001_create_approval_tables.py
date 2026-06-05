"""create approval tables

Revision ID: 001
Revises:
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_tenant_id", "approval_requests", ["tenant_id"])
    op.create_index("ix_approval_requests_request_type", "approval_requests", ["request_type"])
    op.create_index("ix_approval_requests_reference_id", "approval_requests", ["reference_id"])

    op.create_table(
        "approval_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("approval_request_id", sa.Uuid(), nullable=False),
        sa.Column("approver_role", sa.String(50), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_steps_tenant_id", "approval_steps", ["tenant_id"])
    op.create_index(
        "ix_approval_steps_approval_request_id", "approval_steps", ["approval_request_id"]
    )
    op.create_foreign_key(
        "fk_approval_steps_request_id", "approval_steps", "approval_requests",
        ["approval_request_id"], ["id"], ondelete="CASCADE"
    )

    op.create_table(
        "approval_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("approval_step_id", sa.Uuid(), nullable=False),
        sa.Column("approver_id", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_comments_tenant_id", "approval_comments", ["tenant_id"])
    op.create_index(
        "ix_approval_comments_approval_step_id", "approval_comments", ["approval_step_id"]
    )
    op.create_foreign_key(
        "fk_approval_comments_step_id", "approval_comments", "approval_steps",
        ["approval_step_id"], ["id"], ondelete="CASCADE"
    )

    for table in ("approval_requests", "approval_steps", "approval_comments"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'''
            CREATE POLICY tenant_isolation ON "{table}"
            USING (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
                OR current_setting('app.current_tenant_id', true) IS NULL
                OR current_setting('app.current_tenant_id', true) = ''
            )
        ''')


def downgrade():
    op.drop_table("approval_comments")
    op.drop_table("approval_steps")
    op.drop_table("approval_requests")
