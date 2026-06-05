"""CloudEvents-formatted Kafka publisher for Inventory domain."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from typing import Any

from aiokafka import AIOKafkaProducer
from app.config import settings

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await _producer.start()


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, event_type: str, tenant_id: str, data: dict[str, Any]) -> None:
    """Publish a CloudEvents 1.0 message to Kafka. No-op if producer not started."""
    if _producer is None:
        return

    event = {
        "specversion": "1.0",
        "type": event_type,
        "source": "/services/inventory",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "tenantid": tenant_id,
        "correlationid": str(uuid.uuid4()),
        "data": data,
    }
    await _producer.send_and_wait(
        topic,
        value=event,
        headers=[("tenantid", tenant_id.encode())],
    )
