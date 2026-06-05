"""Unit tests for the Level-4 policy engine (no DB, no LLM)."""
from app.models import Decision, ExecutionPolicy
from app.policy import evaluate


def _policy(**kw):
    base = dict(
        tenant_id=__import__("uuid").uuid4(),
        agent_type="procurement_reorder",
        auto_execute_enabled=True,
        max_auto_qty=50,
        max_auto_value=None,
        allowed_urgencies=["normal", "high"],
    )
    base.update(kw)
    return ExecutionPolicy(**base)


def _rec(qty=18, urgency="normal"):
    return {"product_sku": "SKU-1", "recommended_qty": qty, "urgency": urgency}


def test_no_policy_escalates():
    d = evaluate(None, _rec())
    assert d.decision == Decision.escalate
    assert not d.is_auto


def test_disabled_policy_escalates():
    d = evaluate(_policy(auto_execute_enabled=False), _rec())
    assert d.decision == Decision.escalate


def test_within_envelope_auto_executes():
    d = evaluate(_policy(), _rec(qty=18, urgency="normal"))
    assert d.decision == Decision.auto_execute
    assert d.is_auto


def test_qty_over_max_escalates():
    d = evaluate(_policy(max_auto_qty=10), _rec(qty=18))
    assert d.decision == Decision.escalate
    assert "exceeds max_auto_qty" in d.reason


def test_urgency_not_allowed_escalates():
    d = evaluate(_policy(allowed_urgencies=["normal"]), _rec(urgency="critical"))
    assert d.decision == Decision.escalate
    assert "urgency" in d.reason


def test_nonpositive_qty_escalates():
    d = evaluate(_policy(), _rec(qty=0))
    assert d.decision == Decision.escalate


def test_value_ceiling_escalates():
    d = evaluate(_policy(max_auto_value=100.0), _rec(qty=20), unit_cost=10.0)  # 200 > 100
    assert d.decision == Decision.escalate
    assert "max_auto_value" in d.reason


def test_value_ceiling_within_auto_executes():
    d = evaluate(_policy(max_auto_value=500.0), _rec(qty=20), unit_cost=10.0)  # 200 <= 500
    assert d.decision == Decision.auto_execute
