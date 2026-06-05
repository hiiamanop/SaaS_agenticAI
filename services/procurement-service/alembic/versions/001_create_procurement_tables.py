"""create procurement tables

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
        "requisitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requisitions_tenant_id", "requisitions", ["tenant_id"])
    op.create_index("ix_requisitions_product_sku", "requisitions", ["product_sku"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("requisition_id", sa.Uuid(), nullable=True),
        sa.Column("vendor_id", sa.Uuid(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_order_number", "purchase_orders", ["order_number"])
    op.create_index("ix_purchase_orders_requisition_id", "purchase_orders", ["requisition_id"])
    op.create_index("ix_purchase_orders_vendor_id", "purchase_orders", ["vendor_id"])
    op.create_index("ix_purchase_orders_tenant_status", "purchase_orders", ["tenant_id", "status"])

    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid(), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_price", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_items_tenant_id", "purchase_order_items", ["tenant_id"])
    op.create_index(
        "ix_purchase_order_items_purchase_order_id",
        "purchase_order_items",
        ["purchase_order_id"],
    )
    op.create_foreign_key(
        "fk_po_items_po_id", "purchase_order_items", "purchase_orders",
        ["purchase_order_id"], ["id"], ondelete="CASCADE"
    )

    for table in ("requisitions", "purchase_orders", "purchase_order_items"):
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
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("requisitions")
