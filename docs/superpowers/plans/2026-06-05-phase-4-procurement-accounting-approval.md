# Phase 4: Procurement + Accounting + Approval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the core ERP domains: Procurement Service (purchase orders to vendors), Accounting Service (invoices, payments, journal entries), and Approval Service (request workflow engine). Implement cross-domain Kafka events proving the full multi-service SaaS architecture works end-to-end.

**Architecture:** Three new FastAPI services (Procurement, Accounting, Approval), each with PostgreSQL database + RLS. 

- **Procurement**: Creates POs from internal requisitions, publishes `procurement.po.created`
- **Accounting**: Receives PO events, creates vendor invoices, tracks payments, publishes `accounting.invoice.created` and `accounting.payment.recorded`
- **Approval**: Workflow engine for multi-level approvals (POs, invoices), publishes `approval.request.created`, `approval.request.approved`, `approval.request.rejected`

Cross-domain flows:
- PO creation → triggers Approval workflow (requires manager approval)
- Invoice creation → requires Accounting approval before payment
- All events logged to Audit Service for compliance

**Tech Stack:** FastAPI, SQLModel, asyncpg, aiokafka, Alembic, RLS, erp-shared, pytest + httpx. Redpanda running locally.

---

## Summary of Tasks

**Task 1:** Procurement Service scaffold + migrations
**Task 2:** Accounting Service scaffold + migrations
**Task 3:** Approval Service scaffold + migrations
**Task 4:** Procurement Service API + 10 tests
**Task 5:** Accounting Service API + consumer + 10 tests
**Task 6:** Approval Service API + consumer + 12 tests
**Task 7:** Cross-domain workflow integration test
**Task 8:** Dockerfiles + CI update
**Task 9:** End-to-end smoke test + final commit (95 total tests)

---

## Procurement Service Models

```python
# Models for requisitions and purchase orders
class Requisition(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    product_sku: str
    quantity: int
    reason: str
    status: str  # draft/approved/rejected
    created_at: datetime

class PurchaseOrder(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    requisition_id: UUID
    order_number: str (unique)
    vendor_id: UUID
    total_amount: float
    status: str  # pending/confirmed/received/cancelled
    created_at: datetime

class PurchaseOrderItem(SQLModel, table=True):
    id: UUID
    purchase_order_id: UUID
    product_sku: str
    quantity: int
    unit_price: float
    created_at: datetime
```

**Events Published:**
- `procurement.po.created` — when PO confirmed
- `procurement.po.received` — when stock received

---

## Accounting Service Models

```python
class Vendor(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    name: str
    email: str
    tax_id: str
    payment_terms: str
    created_at: datetime

class Invoice(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    invoice_number: str (unique)
    po_id: UUID
    vendor_id: UUID
    total_amount: float
    status: str  # pending/approved/paid/cancelled
    created_at: datetime

class InvoiceLineItem(SQLModel, table=True):
    id: UUID
    invoice_id: UUID
    po_item_id: UUID
    quantity: int
    amount: float
    created_at: datetime

class Payment(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: float
    method: str  # bank_transfer/check/credit_card
    reference: str
    payment_date: datetime
    created_at: datetime

class JournalEntry(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    account_code: str
    debit: float
    credit: float
    reference_id: UUID  # invoice or payment
    created_at: datetime
```

**Consumer:** Listens to `procurement.po.created`, auto-creates draft invoice

**Events Published:**
- `accounting.invoice.created`
- `accounting.payment.recorded`

---

## Approval Service Models

```python
class ApprovalRequest(SQLModel, table=True):
    id: UUID
    tenant_id: UUID
    request_type: str  # procurement_po / accounting_invoice
    reference_id: UUID
    status: str  # pending/approved/rejected/expired
    created_at: datetime

class ApprovalStep(SQLModel, table=True):
    id: UUID
    approval_request_id: UUID
    approver_role: str  # manager / director / cfo
    order_number: int  # 1, 2, 3
    status: str  # pending/approved/rejected
    created_at: datetime

class ApprovalComment(SQLModel, table=True):
    id: UUID
    approval_step_id: UUID
    approver_id: str
    message: str
    created_at: datetime
```

**Consumer:** Listens to `procurement.po.created` and `accounting.invoice.created`, creates 3-step workflow

**Workflow:**
1. Manager approval (step 1)
2. Director approval (step 2)
3. CFO approval (step 3) → publishes `approval.request.approved`

**Events Published:**
- `approval.request.created`
- `approval.request.approved`
- `approval.request.rejected`

---

## Test Counts

- **Procurement Service:** 10 tests (requisitions + POs + isolation)
- **Accounting Service:** 10 tests (invoices + payments + consumer + isolation)
- **Approval Service:** 12 tests (requests + workflow + consumer + isolation)
- **Integration test:** cross-domain end-to-end
- **Total Phase 4:** 32 new tests

**Grand Total by end of Phase 4:** 95 tests (7+6+6+16+4+12+12+10+10+12)

---

## Implementation Notes

1. **Scaffold tasks (1-3):** Copy pattern from Phase 2/3 — create pyproject.toml, models, alembic migrations, commit
2. **API tasks (4-6):** TDD — write tests first, implement routes, use Kafka publishers (events.py), consumer patterns
3. **Cross-domain test (Task 7):** Full workflow: Requisition → PO → Approval workflow (3 steps) → Invoice → Payment
4. **Dockerfiles + CI (Task 8):** Same pattern as Phase 2/3
5. **Final smoke test (Task 9):** All 95 tests pass, live verification, commit, push

**All code follows established patterns from Phase 2/3.** Services are independent with clear Kafka event boundaries. RLS is mandatory on all tables.

---

## Next Phases

**Phase 5 (Future):** Analytics, BI dashboards, AI agent decision support
**Phase 6 (Future):** Mobile apps, external integrations, advanced reporting

**Phase 4 completes the core ERP.**
