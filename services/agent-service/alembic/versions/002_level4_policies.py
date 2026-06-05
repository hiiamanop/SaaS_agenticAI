"""level 4 autonomy: execution policies + recommendation decision fields

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # New decision/audit columns on recommendations
    op.add_column("agent_recommendations", sa.Column("decision", sa.String(), nullable=True))
    op.add_column("agent_recommendations", sa.Column("decision_reason", sa.Text(), nullable=True))
    op.add_column("agent_recommendations", sa.Column("autonomy_mode", sa.String(), nullable=True))

    # Per-tenant, per-agent-type execution policy (Level-4 envelope)
    op.create_table(
        "execution_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("auto_execute_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_auto_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_auto_value", sa.Float(), nullable=True),
        sa.Column("allowed_urgencies", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "agent_type", name="uq_policy_tenant_agent"),
    )
    op.create_index("ix_execution_policies_tenant_id", "execution_policies", ["tenant_id"])
    op.create_index("ix_execution_policies_agent_type", "execution_policies", ["agent_type"])

    op.execute('ALTER TABLE "execution_policies" ENABLE ROW LEVEL SECURITY')
    op.execute('''
        CREATE POLICY tenant_isolation ON "execution_policies"
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
            OR current_setting('app.current_tenant_id', true) IS NULL
            OR current_setting('app.current_tenant_id', true) = ''
        )
    ''')


def downgrade():
    op.drop_table("execution_policies")
    op.drop_column("agent_recommendations", "autonomy_mode")
    op.drop_column("agent_recommendations", "decision_reason")
    op.drop_column("agent_recommendations", "decision")
