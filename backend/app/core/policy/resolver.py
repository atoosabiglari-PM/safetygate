from dataclasses import dataclass

from app.core.policy.hierarchy import PolicyProvenance
from app.schemas.runtime import RuntimeDecision

_DECISION_STRENGTH = {
    RuntimeDecision.ALLOW: 1,
    RuntimeDecision.ALLOW_WITH_CONDITIONS: 2,
    RuntimeDecision.HUMAN_REVIEW_REQUIRED: 3,
    RuntimeDecision.DENY: 4,
    RuntimeDecision.NON_OVERRIDABLE_DENY: 5,
}


@dataclass(frozen=True)
class PolicyRuleDecision:
    provenance: PolicyProvenance
    decision: RuntimeDecision
    reason: str


@dataclass(frozen=True)
class PolicyResolution:
    decision: RuntimeDecision
    winning_rule: PolicyRuleDecision
    considered_rules: tuple[PolicyRuleDecision, ...]


def resolve_policy_decisions(
    decisions: list[PolicyRuleDecision],
) -> PolicyResolution:
    if not decisions:
        raise ValueError(
            "At least one policy decision is required."
        )

    winning_rule = min(
        decisions,
        key=lambda item: (
            -_DECISION_STRENGTH[item.decision],
            item.provenance.authority.value,
            item.provenance.rule_id,
        ),
    )

    return PolicyResolution(
        decision=winning_rule.decision,
        winning_rule=winning_rule,
        considered_rules=tuple(decisions),
    )
