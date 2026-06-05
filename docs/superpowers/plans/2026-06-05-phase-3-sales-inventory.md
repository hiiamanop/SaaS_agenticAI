# Phase 3: Sales + Inventory Domains — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Sales Service (quotations, orders, order items) and Inventory Service (stock, warehouses, stock movements). Implement cross-domain Kafka events so that when a sales order is created, inventory stock is automatically reserved. Prove the event-driven architecture spans multiple domains.

**Architecture:** Two new FastAPI services (Sales and Inventory), each with their own PostgreSQL database and RLS. Sales publishes `sales.order.created` events; Inventory consumes them, reserves stock, and publishes `inventory.stock.reserved` back to Kafka. Both services publish to Audit Service for full event traceability.

**Tech Stack:** FastAPI, SQLModel, asyncpg, aiokafka, Alembic, RLS, erp-shared, pytest + httpx. Redpanda running locally.

---

## File Map

```
services/
  sales-service/
    pyproject.toml                              # CREATE
    Dockerfile                                  # CREATE
    alembic.ini                                 # CREATE
    alembic/
      env.py                                    # CREATE
      versions/
        001_create_sales_tables.py              # CREATE
    app/
      __init__.py                               # CREATE
      main.py                                   # CREATE
      config.py                                 # CREATE
      database.py                               # CREATE
      models.py                                 # CREATE — Quotation, Order, OrderItem
      schemas.py                                # CREATE
      dependencies.py                           # CREATE
      events.py                                 # CREATE — Kafka publisher
      routers/
        __init__.py                             # CREATE
        health.py                               # CREATE
        orders.py                               # CREATE
        quotations.py                           # CREATE
    tests/
      __init__.py                               # CREATE
      conftest.py                               # CREATE
      test_orders.py                            # CREATE
      test_quotations.py                        # CREATE
      test_cross_tenant_isolation.py            # CREATE
  inventory-service/
    pyproject.toml                              # CREATE
    Dockerfile                                  # CREATE
    alembic.ini                                 # CREATE
    alembic/
      env.py                                    # CREATE
      versions/
        001_create_inventory_tables.py          # CREATE
    app/
      __init__.py                               # CREATE
      main.py                                   # CREATE
      config.py                                 # CREATE
      database.py                               # CREATE
      models.py                                 # CREATE — Warehouse, Stock, StockMovement
      schemas.py                                # CREATE
      dependencies.py                           # CREATE
      events.py                                 # CREATE — Kafka publisher
      consumer.py                               # CREATE — consumes sales.order.created
      routers/
        __init__.py                             # CREATE
        health.py                               # CREATE
        stock.py                                # CREATE
        warehouses.py                           # CREATE
    tests/
      __init__.py                               # CREATE
      conftest.py                               # CREATE
      test_stock.py                             # CREATE
      test_warehouses.py                        # CREATE
      test_order_to_stock_flow.py               # CREATE
.github/workflows/ci.yml                        # MODIFY — add sales-service and inventory-service jobs
infra/postgres/init.sql                         # MODIFY — add sales_db, inventory_db
```

---

## Task 1: Sales Service — Scaffold + Models + Migrations

Implement sales domain: quotations (price quotes), orders (committed sales), order items (line items with SKU and qty).

**Files:** pyproject.toml, app/{config,database,models,__init__}.py, alembic.ini, alembic/env.py, alembic/versions/001_create_sales_tables.py

**Code is in this document.** Install deps, run migration, commit.

---

## Task 2: Inventory Service — Scaffold + Models + Migrations

Implement inventory domain: warehouses, stock (qty_on_hand, qty_reserved, qty_available), stock movements (ledger).

**Files:** pyproject.toml, app/{config,database,models,__init__}.py, alembic.ini, alembic/env.py, alembic/versions/001_create_inventory_tables.py

**Code is in this document.** Same pattern as Task 1.

---

## Task 3: Sales Service — API + Kafka Publisher + 12 Tests

**Tests (TDD):**
- test_health
- test_create_order (POST /orders/ → 201 with order_number auto-generated)
- test_get_order
- test_list_orders_by_tenant
- test_update_order_status (PATCH /orders/{id} status→confirmed publishes sales.order.created)
- test_orders_isolated_by_tenant
- test_create_quotation (POST /quotations/)
- test_get_quotation
- test_update_quotation_status
- test_convert_quotation_to_order (POST /quotations/{id}/convert)
- test_quotations_isolated_by_tenant

**Files:**
- `app/schemas.py` — QuotationCreate, QuotationRead, OrderCreate, OrderRead, OrderUpdate
- `app/dependencies.py` — get_current_user from erp-shared
- `app/events.py` — CloudEvents publisher (same pattern as CRM)
- `app/routers/health.py`
- `app/routers/quotations.py`
- `app/routers/orders.py`
- `app/main.py` — lifespan with start_producer/stop_producer
- `tests/conftest.py`, `test_quotations.py`, `test_orders.py`, `test_tenant_isolation.py`

**Expected:** 12 tests pass.

---

## Task 4: Inventory Service — API + Kafka Consumer + 11 Tests

**Tests (TDD):**
- test_health
- test_create_warehouse
- test_list_warehouses
- test_create_stock (POST /stock/)
- test_get_stock
- test_list_stock_by_warehouse
- test_reserve_stock (POST /stock/{id}/reserve with quantity)
- test_release_stock (POST /stock/{id}/release with quantity)
- test_stock_movement_recorded (verify ledger created)
- test_consume_order_event (consumer subscribes to sales.order.created, reserves stock, publishes inventory.stock.reserved)
- test_warehouses_isolated_by_tenant
- test_stock_isolated_by_tenant

**Files:**
- `app/schemas.py`
- `app/dependencies.py`
- `app/events.py` — Kafka publisher
- `app/consumer.py` — Consumes sales.order.created, reserves stock
- `app/routers/{health,warehouses,stock}.py`
- `app/main.py` — lifespan starts consumer as background task
- `tests/conftest.py`, `test_warehouses.py`, `test_stock.py`, `test_consumer.py`

**Consumer flow:**
1. Subscribe to sales.order.created topic
2. Parse event: extract tenant_id, order_items (product_sku, quantity)
3. For each item: find Stock record, decrement quantity_available, increment quantity_reserved
4. Create StockMovement records (type=reservation)
5. Publish inventory.stock.reserved event
6. Never crash on malformed events (log warning)

**Expected:** 11 tests pass.

---

## Task 5: Cross-Domain Integration Test

**Smoke test verifying end-to-end flow:**

1. Create warehouse in Inventory Service
2. Create stock entry (product SKU, qty_on_hand=100)
3. Create order in Sales Service with order items (SKU, qty=10)
4. Verify order status → confirmed
5. Verify sales.order.created published to Kafka
6. Wait 1 second (consumer async processing)
7. Verify Inventory Service consumed event
8. Check stock: qty_available should be 90, qty_reserved should be 10
9. Check stock_movements: should have 1 entry (type=reservation)
10. Verify inventory.stock.reserved published to Kafka

All 4 events (sales.order.created, inventory.stock.reserved + 2 audit events) should be visible in Redpanda Console.

---

## Task 6: Dockerfiles + CI Update

Create Dockerfiles for both services, add CI jobs (same pattern as Phase 2).

**Files:**
- `services/sales-service/Dockerfile`
- `services/inventory-service/Dockerfile`
- Update `.github/workflows/ci.yml` with test-sales-service and test-inventory-service jobs

---

## Task 7: End-to-End Smoke Test + Final Commit

**Run all tests:**
```bash
erp-shared (7) + tenant (6) + subscription (6) + crm (16) + audit (4) + sales (12) + inventory (11) = 62 total
```

**Live verification:**
1. Start Sales Service on port 8002
2. Create order with order_items
3. Confirm order (should publish sales.order.created)
4. Verify event in Redpanda Console
5. Verify Inventory Service consumed and reserved stock
6. Final commit: Phase 3 complete, all 62 tests passing

---

## Next Phase (Phase 4)

Procurement Service (purchase orders), Accounting Service (invoices, payments), and Approval Service (request workflow) — completing the core ERP features.
