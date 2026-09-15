from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.resolver import (
    PolicyRuleDecision,
    merge_runtime_and_policy_decision,
    resolve_policy_decisions,
)
from app.schemas.runtime import (
    RuntimeDecision,
    RuntimeDecisionResult,
)


def make_policy(
    decision: RuntimeDecision,
    *,
    reason: str = "OPA policy decision.",
    conditions: tuple[str, ...] = (),
):
    rule = PolicyRuleDecision(
        provenance=PolicyProvenance(
            rule_id="opa.rule.test",
            authority=PolicyAuthority.ORGANIZATION_POLICY,
            source_name="SafetyGate OPA policy",
            source_version="v1",
        ),
        decision=decision,
        reason=reason,
        conditions=conditions,
    )

    return resolve_policy_decisions([rule])


def test_policy_can_make_allow_more_restrictive() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=["Runtime checks passed."],
    )

    policy = make_policy(RuntimeDecision.DENY)

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert result.decision == RuntimeDecision.DENY
    assert "Runtime checks passed." in result.reasons
    assert "OPA policy decision." in result.reasons


def test_policy_allow_cannot_override_runtime_deny() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.DENY,
        reasons=["Runtime denied the action."],
    )

    policy = make_policy(RuntimeDecision.ALLOW)

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert result.decision == RuntimeDecision.DENY
    assert result.reasons == [
        "Runtime denied the action."
    ]


def test_policy_cannot_override_non_overridable_deny() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
        reasons=["Hard SafetyGate boundary."],
    )

    policy = make_policy(RuntimeDecision.ALLOW)

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert (
        result.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )


def test_policy_can_require_human_review() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=["Runtime checks passed."],
    )

    policy = make_policy(
        RuntimeDecision.HUMAN_REVIEW_REQUIRED
    )

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert (
        result.decision
        == RuntimeDecision.HUMAN_REVIEW_REQUIRED
    )


def test_policy_conditions_are_added_when_more_restrictive() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=["Runtime checks passed."],
    )

    policy = make_policy(
        RuntimeDecision.ALLOW_WITH_CONDITIONS,
        conditions=(
            "Record enhanced audit evidence.",
            "Verify execution result.",
        ),
    )

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert (
        result.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )
    assert result.conditions == [
        "Record enhanced audit evidence.",
        "Verify execution result.",
    ]


def test_runtime_conditions_survive_less_restrictive_policy() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
        reasons=["Runtime requires controls."],
        conditions=[
            "Record full audit evidence.",
            "Verify execution result.",
        ],
    )

    policy = make_policy(RuntimeDecision.ALLOW)

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert (
        result.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )
    assert result.conditions == [
        "Record full audit evidence.",
        "Verify execution result.",
    ]


def test_equal_conditional_decisions_merge_without_duplicates() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
        reasons=["Runtime requires controls."],
        conditions=[
            "Verify execution result.",
        ],
    )

    policy = make_policy(
        RuntimeDecision.ALLOW_WITH_CONDITIONS,
        conditions=(
            "Verify execution result.",
            "Record enhanced audit evidence.",
        ),
    )

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert result.conditions == [
        "Verify execution result.",
        "Record enhanced audit evidence.",
    ]


def test_all_equally_restrictive_policy_conditions_are_preserved() -> None:
    runtime = RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=["Runtime checks passed."],
    )

    first = PolicyRuleDecision(
        provenance=PolicyProvenance(
            rule_id="opa.condition.first",
            authority=PolicyAuthority.ORGANIZATION_POLICY,
            source_name="SafetyGate OPA policy",
            source_version="v1",
        ),
        decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
        reason="First policy condition.",
        conditions=("Condition A.",),
    )

    second = PolicyRuleDecision(
        provenance=PolicyProvenance(
            rule_id="opa.condition.second",
            authority=PolicyAuthority.ORGANIZATION_POLICY,
            source_name="SafetyGate OPA policy",
            source_version="v1",
        ),
        decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
        reason="Second policy condition.",
        conditions=("Condition B.",),
    )

    policy = resolve_policy_decisions(
        [first, second]
    )

    result = merge_runtime_and_policy_decision(
        runtime_result=runtime,
        policy_resolution=policy,
    )

    assert (
        result.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )
    assert result.conditions == [
        "Condition A.",
        "Condition B.",
    ]
