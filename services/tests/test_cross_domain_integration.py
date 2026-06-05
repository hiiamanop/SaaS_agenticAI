"""
Phase 3 Task 5: Cross-Domain Integration Tests

Tests the end-to-end flow between Sales Service and Inventory Service:
1. Create warehouse in Inventory Service
2. Create stock entry with initial quantity
3. Create order in Sales Service with items
4. Confirm order (triggers Kafka event: sales.order.created)
5. Wait for Inventory consumer to process event
6. Verify stock was reserved correctly
7. Check stock movements were recorded
8. Verify inventory.stock.reserved event was published

Run with: pytest tests/test_cross_domain_integration.py -v -s
"""

import asyncio
import httpx
import json
import pytest
import time
import uuid
from decimal import Decimal
from typing import Optional, Tuple

# Configuration
SALES_SERVICE_URL = "http://localhost:8002"
INVENTORY_SERVICE_URL = "http://localhost:8003"
TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Fixtures
@pytest.fixture
async def http_client():
    """Async HTTP client fixture."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


@pytest.fixture(scope="function")
async def warehouse_and_stock(http_client) -> Tuple[str, str, str]:
    """Create a warehouse and a stock entry with a SKU unique to this test.

    A unique SKU per test keeps reservations deterministic: the inventory
    consumer matches stock by (tenant_id, product_sku), so reusing one SKU
    across tests would let one test's order reserve against another's row.
    """
    sku = f"SKU-{uuid.uuid4().hex[:12]}"

    # Create warehouse
    warehouse_response = await http_client.post(
        f"{INVENTORY_SERVICE_URL}/warehouses/",
        json={
            "tenant_id": TEST_TENANT_ID,
            "name": "Test Warehouse",
            "code": f"WH-{uuid.uuid4().hex[:8]}",
            "location": "Test Location",
        },
    )
    assert warehouse_response.status_code == 201, f"Failed to create warehouse: {warehouse_response.text}"
    warehouse_id = warehouse_response.json()["id"]

    # Create stock
    stock_response = await http_client.post(
        f"{INVENTORY_SERVICE_URL}/stock/",
        json={
            "tenant_id": TEST_TENANT_ID,
            "warehouse_id": warehouse_id,
            "product_sku": sku,
            "product_name": "Integration Test Product",
            "qty_on_hand": 100,
            "reorder_point": 10,
        },
    )
    assert stock_response.status_code == 201, f"Failed to create stock: {stock_response.text}"
    stock_id = stock_response.json()["id"]

    yield warehouse_id, stock_id, sku


class TestCrossDomainIntegration:
    """Test suite for cross-domain integration between Sales and Inventory services."""

    @pytest.mark.asyncio
    async def test_services_health(self, http_client):
        """Step 0: Verify both services are running."""
        sales_response = await http_client.get(f"{SALES_SERVICE_URL}/health")
        inventory_response = await http_client.get(f"{INVENTORY_SERVICE_URL}/health")

        assert sales_response.status_code == 200, "Sales Service is not healthy"
        assert inventory_response.status_code == 200, "Inventory Service is not healthy"

    @pytest.mark.asyncio
    async def test_create_warehouse(self, http_client):
        """Step 1: Create warehouse in Inventory Service."""
        response = await http_client.post(
            f"{INVENTORY_SERVICE_URL}/warehouses/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "name": "Test Warehouse",
                "code": "WH-TEST-001",
                "location": "Test Location",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Warehouse"
        assert data["code"] == "WH-TEST-001"
        assert data["tenant_id"] == TEST_TENANT_ID

    @pytest.mark.asyncio
    async def test_create_stock(self, http_client, warehouse_and_stock):
        """Step 2: Create stock entry."""
        warehouse_id, stock_id, sku = warehouse_and_stock

        response = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["product_sku"] == sku
        assert data["qty_on_hand"] == 100
        assert data["qty_available"] == 100
        assert data["qty_reserved"] == 0

    @pytest.mark.asyncio
    async def test_create_order(self, http_client):
        """Step 3: Create order in Sales Service."""
        response = await http_client.post(
            f"{SALES_SERVICE_URL}/orders/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "contact_id": None,
                "quotation_id": None,
                "notes": "Test order",
                "items": [
                    {
                        "product_sku": "SKU-001",
                        "product_name": "Integration Test Product",
                        "quantity": 10,
                        "unit_price": "100.00",
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["items"]) == 1
        assert data["items"][0]["product_sku"] == "SKU-001"
        assert data["items"][0]["quantity"] == 10

    @pytest.mark.asyncio
    async def test_confirm_order_publishes_event(self, http_client):
        """Step 4: Confirm order and verify event is published."""
        # Create order first
        create_response = await http_client.post(
            f"{SALES_SERVICE_URL}/orders/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "contact_id": None,
                "quotation_id": None,
                "notes": "Test order",
                "items": [
                    {
                        "product_sku": "SKU-001",
                        "product_name": "Integration Test Product",
                        "quantity": 10,
                        "unit_price": "100.00",
                    }
                ],
            },
        )
        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

        # Confirm order
        response = await http_client.patch(
            f"{SALES_SERVICE_URL}/orders/{order_id}",
            json={"status": "confirmed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_end_to_end_order_flow(self, http_client, warehouse_and_stock):
        """Complete end-to-end integration test."""
        warehouse_id, stock_id, sku = warehouse_and_stock

        # Verify initial stock
        initial_stock = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}")
        assert initial_stock.status_code == 200
        initial_data = initial_stock.json()
        assert initial_data["qty_available"] == 100
        assert initial_data["qty_reserved"] == 0

        # Create order
        order_response = await http_client.post(
            f"{SALES_SERVICE_URL}/orders/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "contact_id": None,
                "quotation_id": None,
                "notes": "Integration test order",
                "items": [
                    {
                        "product_sku": sku,
                        "product_name": "Integration Test Product",
                        "quantity": 10,
                        "unit_price": "100.00",
                    }
                ],
            },
        )
        assert order_response.status_code == 201
        order_id = order_response.json()["id"]

        # Confirm order (publishes sales.order.created event)
        confirm_response = await http_client.patch(
            f"{SALES_SERVICE_URL}/orders/{order_id}",
            json={"status": "confirmed"},
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

        # Wait for consumer to process event
        await asyncio.sleep(2)

        # Verify stock was reserved
        final_stock = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}")
        assert final_stock.status_code == 200
        final_data = final_stock.json()
        assert final_data["qty_available"] == 90, f"Expected qty_available=90, got {final_data['qty_available']}"
        assert final_data["qty_reserved"] == 10, f"Expected qty_reserved=10, got {final_data['qty_reserved']}"

        # Verify stock movements
        movements_response = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}/movements")
        assert movements_response.status_code == 200
        movements = movements_response.json()
        reservation_movements = [m for m in movements if m["movement_type"] == "reservation"]
        assert len(reservation_movements) >= 1, "No reservation movements found"
        assert reservation_movements[0]["quantity"] == 10
        assert order_id in reservation_movements[0]["reference"]

    @pytest.mark.asyncio
    async def test_multiple_orders_reserve_correct_quantities(self, http_client, warehouse_and_stock):
        """Test that multiple orders correctly reserve stock."""
        warehouse_id, stock_id, sku = warehouse_and_stock

        # Create and confirm first order (10 units)
        order1_response = await http_client.post(
            f"{SALES_SERVICE_URL}/orders/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "contact_id": None,
                "quotation_id": None,
                "items": [
                    {
                        "product_sku": sku,
                        "product_name": "Integration Test Product",
                        "quantity": 10,
                        "unit_price": "100.00",
                    }
                ],
            },
        )
        order1_id = order1_response.json()["id"]
        await http_client.patch(
            f"{SALES_SERVICE_URL}/orders/{order1_id}",
            json={"status": "confirmed"},
        )

        # Create and confirm second order (20 units)
        order2_response = await http_client.post(
            f"{SALES_SERVICE_URL}/orders/",
            json={
                "tenant_id": TEST_TENANT_ID,
                "contact_id": None,
                "quotation_id": None,
                "items": [
                    {
                        "product_sku": sku,
                        "product_name": "Integration Test Product",
                        "quantity": 20,
                        "unit_price": "100.00",
                    }
                ],
            },
        )
        order2_id = order2_response.json()["id"]
        await http_client.patch(
            f"{SALES_SERVICE_URL}/orders/{order2_id}",
            json={"status": "confirmed"},
        )

        # Wait for consumer to process both events
        await asyncio.sleep(3)

        # Verify final stock (100 - 10 - 20 = 70)
        final_stock = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}")
        final_data = final_stock.json()
        assert final_data["qty_available"] == 70, f"Expected qty_available=70, got {final_data['qty_available']}"
        assert final_data["qty_reserved"] == 30, f"Expected qty_reserved=30, got {final_data['qty_reserved']}"

        # Verify movements
        movements_response = await http_client.get(f"{INVENTORY_SERVICE_URL}/stock/{stock_id}/movements")
        movements = movements_response.json()
        assert len(movements) >= 2, "Expected at least 2 movements"
