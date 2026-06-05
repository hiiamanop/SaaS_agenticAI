# services/audit-service/tests/test_audit_consumer.py
import pytest
import uuid
import json
from datetime import datetime, UTC
from sqlmodel import select
from app.models import AuditLog
from app.consumer import process_event


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_process_event_saves_to_db(db_session):
    event_payload = json.dumps({
        "specversion": "1.0",
        "type": "crm.lead.qualified",
        "source": "/services/crm",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "tenantid": str(uuid.uuid4()),
        "data": {"lead_id": str(uuid.uuid4()), "email": "test@test.com"},
    }).encode()

    await process_event("crm.lead.qualified", event_payload, db_session)
    await db_session.commit()

    result = await db_session.execute(select(AuditLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == "crm.lead.qualified"
    assert logs[0].topic == "crm.lead.qualified"


@pytest.mark.asyncio
async def test_process_malformed_event_does_not_crash(db_session):
    await process_event("crm.lead.qualified", b"not valid json", db_session)


@pytest.mark.asyncio
async def test_audit_log_stores_tenant_id(db_session):
    tenant_id = str(uuid.uuid4())
    event_payload = json.dumps({
        "specversion": "1.0",
        "type": "sales.order.created",
        "source": "/services/sales",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "tenantid": tenant_id,
        "data": {"order_id": "ord-001"},
    }).encode()

    await process_event("sales.order.created", event_payload, db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.tenant_id == tenant_id
