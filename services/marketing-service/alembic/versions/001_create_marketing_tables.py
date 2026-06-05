"""create marketing tables

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
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("pain_points", sa.Text(), nullable=True),
        sa.Column("value_proposition", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_tenant_status", "campaigns", ["tenant_id", "status"])

    op.create_table(
        "company_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("decision_makers", sa.Text(), nullable=True),
        sa.Column("pain_point_match", sa.Float(), nullable=True),
        sa.Column("contact_validation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="discovered"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_targets_tenant_id", "company_targets", ["tenant_id"])
    op.create_index("ix_company_targets_campaign_id", "company_targets", ["campaign_id"])
    op.create_foreign_key(
        "fk_company_targets_campaign_id",
        "company_targets", "campaigns",
        ["campaign_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "content_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("asset_metadata", sa.JSON(), nullable=True),
        sa.Column("publish_status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("engagement_metrics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_assets_tenant_id", "content_assets", ["tenant_id"])
    op.create_index("ix_content_assets_campaign_id", "content_assets", ["campaign_id"])
    op.create_foreign_key(
        "fk_content_assets_campaign_id",
        "content_assets", "campaigns",
        ["campaign_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("creative_json", sa.JSON(), nullable=True),
        sa.Column("targeting_json", sa.JSON(), nullable=True),
        sa.Column("daily_budget", sa.Float(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_campaigns_tenant_id", "ad_campaigns", ["tenant_id"])
    op.create_index("ix_ad_campaigns_campaign_id", "ad_campaigns", ["campaign_id"])
    op.create_foreign_key(
        "fk_ad_campaigns_campaign_id",
        "ad_campaigns", "campaigns",
        ["campaign_id"], ["id"],
        ondelete="CASCADE",
    )

    for table in ("campaigns", "company_targets", "content_assets", "ad_campaigns"):
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
    op.drop_table("ad_campaigns")
    op.drop_table("content_assets")
    op.drop_table("company_targets")
    op.drop_table("campaigns")
