"""create agent tables

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
        "agent_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("input_context", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="proposed"),
        sa.Column("approval_request_id", sa.Uuid(), nullable=True),
        sa.Column("executed_ref_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_recommendations_tenant_id", "agent_recommendations", ["tenant_id"])
    op.create_index("ix_agent_recommendations_agent_type", "agent_recommendations", ["agent_type"])
    op.create_index(
        "ix_agent_recommendations_approval_request_id",
        "agent_recommendations",
        ["approval_request_id"],
    )

    op.create_table(
        "agent_action_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_action_logs_tenant_id", "agent_action_logs", ["tenant_id"])
    op.create_index(
        "ix_agent_action_logs_recommendation_id", "agent_action_logs", ["recommendation_id"]
    )

    for table in ("agent_recommendations", "agent_action_logs"):
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
    op.drop_table("agent_action_logs")
    op.drop_table("agent_recommendations")
