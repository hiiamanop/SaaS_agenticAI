#!/usr/bin/env bash
# scripts/bootstrap-topics.sh
# Creates all required Kafka topics in Redpanda.
# Safe to run multiple times — skips existing topics.
set -e

PARTITIONS=3
REPLICATION=1

echo "Creating Kafka topics in Redpanda..."

create_topic() {
  local topic="$1"
  docker exec erp_redpanda rpk topic create "$topic" \
    --brokers "redpanda:9092" \
    --partitions "$PARTITIONS" \
    --replicas "$REPLICATION" \
    2>/dev/null && echo "  ✓ $topic" || echo "  ~ $topic (already exists)"
}

# Identity
create_topic "identity.tenant.created"
create_topic "identity.tenant.suspended"
create_topic "identity.user.role.changed"

# Sales
create_topic "sales.order.created"
create_topic "sales.order.approved"

# Inventory
create_topic "inventory.stock.low"
create_topic "inventory.stock.reserved"

# Procurement
create_topic "procurement.po.requested"
create_topic "procurement.po.approved"
create_topic "procurement.goods.received"

# Accounting
create_topic "accounting.invoice.generated"
create_topic "accounting.payment.processed"
create_topic "accounting.budget.alert"

# Approvals
create_topic "approval.request.created"
create_topic "approval.request.approved"
create_topic "approval.request.rejected"

# Agent events
create_topic "agent.action.recommended"
create_topic "agent.action.approved"
create_topic "agent.action.executed"
create_topic "agent.workflow.failed"

# Dead Letter Queue
create_topic "dlq.all"

echo ""
echo "Topics ready. Verify at: http://redpanda.localhost"
