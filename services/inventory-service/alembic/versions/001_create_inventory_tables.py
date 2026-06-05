"""create inventory tables

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
        "warehouses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])
    op.create_index("ix_warehouses_code", "warehouses", ["code"])
    op.create_index("ix_warehouses_tenant_code", "warehouses", ["tenant_id", "code"])

    op.create_table(
        "stock",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("qty_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_tenant_id", "stock", ["tenant_id"])
    op.create_index("ix_stock_warehouse_id", "stock", ["warehouse_id"])
    op.create_index("ix_stock_product_sku", "stock", ["product_sku"])
    op.create_index("ix_stock_tenant_sku", "stock", ["tenant_id", "product_sku"])
    op.create_foreign_key(
        "fk_stock_warehouse_id", "stock", "warehouses",
        ["warehouse_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("stock_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_tenant_id", "stock_movements", ["tenant_id"])
    op.create_index("ix_stock_movements_stock_id", "stock_movements", ["stock_id"])
    op.create_index("ix_stock_movements_type", "stock_movements", ["movement_type"])
    op.create_foreign_key(
        "fk_stock_movements_stock_id", "stock_movements", "stock",
        ["stock_id"], ["id"], ondelete="CASCADE"
    )

    for table in ("warehouses", "stock", "stock_movements"):
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
    op.drop_table("stock_movements")
    op.drop_table("stock")
    op.drop_table("warehouses")
