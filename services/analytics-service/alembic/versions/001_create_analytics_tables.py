"""create analytics read-model tables

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
        "revenue_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenue_total", sa.Numeric(16, 2), nullable=False, server_default="0.00"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revenue_daily_tenant_id", "revenue_daily", ["tenant_id"])
    op.create_index("ix_revenue_daily_day", "revenue_daily", ["day"])
    op.create_index(
        "uq_revenue_daily_tenant_day", "revenue_daily", ["tenant_id", "day"], unique=True
    )

    op.create_table(
        "procurement_spend",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("po_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("po_total", sa.Numeric(16, 2), nullable=False, server_default="0.00"),
        sa.Column("invoice_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoice_total", sa.Numeric(16, 2), nullable=False, server_default="0.00"),
        sa.Column("paid_total", sa.Numeric(16, 2), nullable=False, server_default="0.00"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_procurement_spend_tenant"),
    )
    op.create_index("ix_procurement_spend_tenant_id", "procurement_spend", ["tenant_id"])

    op.create_table(
        "inventory_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("qty_reserved_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_stock_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_signals_tenant_id", "inventory_signals", ["tenant_id"])
    op.create_index("ix_inventory_signals_product_sku", "inventory_signals", ["product_sku"])
    op.create_index(
        "uq_inventory_signals_tenant_sku",
        "inventory_signals",
        ["tenant_id", "product_sku"],
        unique=True,
    )

    for table in ("revenue_daily", "procurement_spend", "inventory_signals"):
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
    op.drop_table("inventory_signals")
    op.drop_table("procurement_spend")
    op.drop_table("revenue_daily")
