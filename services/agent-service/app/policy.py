"""Level-4 execution policy engine.

Decides whether a recommendation may auto-execute or must escalate to a human.
Pure and deterministic — no DB, no LLM — so it is trivially unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Decision, ExecutionPolicy


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str

    @property
    def is_auto(self) -> bool:
        return self.decision == Decision.auto_execute


def evaluate(
    policy: Optional[ExecutionPolicy],
    recommendation: dict,
    unit_cost: Optional[float] = None,
) -> PolicyDecision:
    """Route a recommendation. Default-off semantics: no policy or a disabled one
    always escalates, so a tenant that never opts in keeps Level-3 behavior."""
    if policy is None or not policy.auto_execute_enabled:
        return PolicyDecision(Decision.escalate, "auto-execution not enabled for this tenant/agent")

    qty = int(recommendation.get("recommended_qty", 0) or 0)
    urgency = str(recommendation.get("urgency", "")).lower()

    if qty <= 0:
        return PolicyDecision(Decision.escalate, f"non-positive recommended_qty ({qty})")

    allowed = [str(u).lower() for u in (policy.allowed_urgencies or [])]
    if urgency not in allowed:
        return PolicyDecision(
            Decision.escalate,
            f"urgency '{urgency}' not in auto-allowed {allowed}",
        )

    if policy.max_auto_qty and qty > policy.max_auto_qty:
        return PolicyDecision(
            Decision.escalate,
            f"qty {qty} exceeds max_auto_qty {policy.max_auto_qty}",
        )

    if policy.max_auto_value is not None and unit_cost is not None:
        value = qty * unit_cost
        if value > policy.max_auto_value:
            return PolicyDecision(
                Decision.escalate,
                f"value {value:.2f} exceeds max_auto_value {policy.max_auto_value:.2f}",
            )

    return PolicyDecision(
        Decision.auto_execute,
        f"qty {qty} within max_auto_qty {policy.max_auto_qty} and urgency '{urgency}' allowed",
    )
