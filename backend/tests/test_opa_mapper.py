import pytest
from app.core.policy.hierarchy import PolicyAuthority
from app.core.policy.opa_mapper import (
    OpaPolicyMappingError,
    build_policy_resolution_from_opa,
    map_opa_rule_decision,
)
from app.schemas.runtime import RuntimeDecision


def make_rule(
    *,
    rule_id: str = "safetygate.runtime.default_allow",
    authority: str = "ORGANIZATION_POLICY",
    decision: str = "ALLOW",
    reason: str = "OPA adds no additional restriction.",
    conditions: list[str] | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "authority": authority,
        "source_name": "SafetyGate OPA runtime policy",
        "source_version": "v1",
        "source_reference": "policies/rego/runtime.rego",
        "decision": decision,
        "reason": reason,
        "conditions": conditions or [],
    }


def test_maps_valid_opa_rule() -> None:
    rule = map_opa_rule_decision(
        make_rule(
            decision="ALLOW_WITH_CONDITIONS",
            conditions=[
                "Record full audit evidence.",
                "Verify execution result.",
            ],
        )
    )

    assert (
        rule.provenance.authority
        == PolicyAuthority.ORGANIZATION_POLICY
    )
    assert (
        rule.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )
    assert rule.conditions == (
        "Record full audit evidence.",
        "Verify execution result.",
    )


def test_resolution_selects_most_restrictive_opa_rule() -> None:
    rules = (
        make_rule(),
        make_rule(
            rule_id="safetygate.runtime.medium_risk_controls",
            decision="ALLOW_WITH_CONDITIONS",
            reason="Additional controls required.",
        ),
        make_rule(
            rule_id="safetygate.runtime.prohibited",
            decision="DENY",
            reason="Action denied by policy.",
        ),
    )

    resolution = build_policy_resolution_from_opa(rules)

    assert resolution.decision == RuntimeDecision.DENY
    assert (
        resolution.winning_rule.provenance.rule_id
        == "safetygate.runtime.prohibited"
    )
    assert len(resolution.considered_rules) == 3


def test_unknown_authority_fails_closed() -> None:
    with pytest.raises(
        OpaPolicyMappingError,
        match="Unknown OPA policy authority",
    ):
        map_opa_rule_decision(
            make_rule(
                authority="UNKNOWN_AUTHORITY",
            )
        )


def test_unknown_decision_fails_closed() -> None:
    with pytest.raises(
        OpaPolicyMappingError,
        match="Unknown OPA runtime decision",
    ):
        map_opa_rule_decision(
            make_rule(
                decision="MAYBE",
            )
        )


def test_missing_required_field_fails_closed() -> None:
    rule = make_rule()
    del rule["rule_id"]

    with pytest.raises(
        OpaPolicyMappingError,
        match="rule_id",
    ):
        map_opa_rule_decision(rule)


def test_invalid_conditions_fail_closed() -> None:
    rule = make_rule()
    rule["conditions"] = "not-a-list"

    with pytest.raises(
        OpaPolicyMappingError,
        match="conditions",
    ):
        map_opa_rule_decision(rule)


def test_empty_rule_set_fails_closed() -> None:
    with pytest.raises(
        OpaPolicyMappingError,
        match="At least one OPA policy rule",
    ):
        build_policy_resolution_from_opa(())



def test_opa_rule_order_is_deterministic() -> None:
    rules = (
        make_rule(
            rule_id="safetygate.runtime.z_rule",
        ),
        make_rule(
            rule_id="safetygate.runtime.a_rule",
        ),
    )

    resolution = build_policy_resolution_from_opa(rules)

    assert [
        item.provenance.rule_id
        for item in resolution.considered_rules
    ] == [
        "safetygate.runtime.a_rule",
        "safetygate.runtime.z_rule",
    ]
