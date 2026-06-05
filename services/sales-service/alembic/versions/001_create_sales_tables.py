"""create sales tables

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
        "quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_number", sa.String(50), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotations_tenant_id", "quotations", ["tenant_id"])
    op.create_index("ix_quotations_quotation_number", "quotations", ["quotation_number"])
    op.create_index("ix_quotations_contact_id", "quotations", ["contact_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_tenant_id", "orders", ["tenant_id"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])
    op.create_index("ix_orders_quotation_id", "orders", ["quotation_id"])
    op.create_index("ix_orders_contact_id", "orders", ["contact_id"])
    op.create_index("ix_orders_tenant_status", "orders", ["tenant_id", "status"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_price", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_tenant_id", "order_items", ["tenant_id"])
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_foreign_key(
        "fk_order_items_order_id", "order_items", "orders",
        ["order_id"], ["id"], ondelete="CASCADE"
    )

    for table in ("quotations", "orders", "order_items"):
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
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("quotations")
