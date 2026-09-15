from dataclasses import dataclass

from app.core.policy.hierarchy import PolicyProvenance
from app.schemas.runtime import (
    RuntimeDecision,
    RuntimeDecisionResult,
)

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
    conditions: tuple[str, ...] = ()


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


def _extend_unique(
    target: list[str],
    values: tuple[str, ...] | list[str],
) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def merge_runtime_and_policy_decision(
    *,
    runtime_result: RuntimeDecisionResult,
    policy_resolution: PolicyResolution,
) -> RuntimeDecisionResult:
    runtime_strength = _DECISION_STRENGTH[
        runtime_result.decision
    ]
    policy_strength = _DECISION_STRENGTH[
        policy_resolution.decision
    ]

    if policy_strength > runtime_strength:
        final_decision = policy_resolution.decision
    else:
        final_decision = runtime_result.decision

    reasons = list(runtime_result.reasons)

    if (
        policy_strength >= runtime_strength
        and policy_resolution.winning_rule.reason
        not in reasons
    ):
        reasons.append(
            policy_resolution.winning_rule.reason
        )

    conditions: list[str] = []

    if final_decision == RuntimeDecision.ALLOW_WITH_CONDITIONS:
        if (
            runtime_result.decision
            == RuntimeDecision.ALLOW_WITH_CONDITIONS
        ):
            _extend_unique(
                conditions,
                runtime_result.conditions,
            )

        if (
            policy_resolution.decision
            == RuntimeDecision.ALLOW_WITH_CONDITIONS
        ):
            for rule in policy_resolution.considered_rules:
                if (
                    rule.decision
                    != RuntimeDecision.ALLOW_WITH_CONDITIONS
                ):
                    continue

                _extend_unique(
                    conditions,
                    rule.conditions,
                )

    return RuntimeDecisionResult(
        decision=final_decision,
        reasons=reasons,
        conditions=conditions,
    )
