import pytest
from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.resolver import (
    PolicyRuleDecision,
    resolve_policy_decisions,
)
from app.schemas.runtime import RuntimeDecision


def make_rule(
    *,
    rule_id: str,
    authority: PolicyAuthority,
    decision: RuntimeDecision,
) -> PolicyRuleDecision:
    return PolicyRuleDecision(
        provenance=PolicyProvenance(
            rule_id=rule_id,
            authority=authority,
            source_name="Test Policy",
            source_version="1.0",
        ),
        decision=decision,
        reason=f"{rule_id} test decision.",
    )


def test_law_deny_beats_organization_allow() -> None:
    resolution = resolve_policy_decisions(
        [
            make_rule(
                rule_id="ORG-ALLOW-001",
                authority=PolicyAuthority.ORGANIZATION_POLICY,
                decision=RuntimeDecision.ALLOW,
            ),
            make_rule(
                rule_id="LAW-DENY-001",
                authority=PolicyAuthority.MANDATORY_LAW,
                decision=RuntimeDecision.DENY,
            ),
        ]
    )

    assert resolution.decision == RuntimeDecision.DENY
    assert resolution.winning_rule.provenance.rule_id == (
        "LAW-DENY-001"
    )


def test_lower_authority_deny_is_not_erased_by_allow() -> None:
    resolution = resolve_policy_decisions(
        [
            make_rule(
                rule_id="LAW-ALLOW-001",
                authority=PolicyAuthority.MANDATORY_LAW,
                decision=RuntimeDecision.ALLOW,
            ),
            make_rule(
                rule_id="SEC-DENY-001",
                authority=PolicyAuthority.SECURITY_STANDARD,
                decision=RuntimeDecision.DENY,
            ),
        ]
    )

    assert resolution.decision == RuntimeDecision.DENY
    assert resolution.winning_rule.provenance.rule_id == (
        "SEC-DENY-001"
    )


def test_equal_restrictions_use_higher_authority_provenance() -> None:
    resolution = resolve_policy_decisions(
        [
            make_rule(
                rule_id="ORG-DENY-001",
                authority=PolicyAuthority.ORGANIZATION_POLICY,
                decision=RuntimeDecision.DENY,
            ),
            make_rule(
                rule_id="SEC-DENY-001",
                authority=PolicyAuthority.SECURITY_STANDARD,
                decision=RuntimeDecision.DENY,
            ),
        ]
    )

    assert resolution.decision == RuntimeDecision.DENY
    assert resolution.winning_rule.provenance.authority == (
        PolicyAuthority.SECURITY_STANDARD
    )


def test_non_overridable_deny_is_strongest() -> None:
    resolution = resolve_policy_decisions(
        [
            make_rule(
                rule_id="HUMAN-ALLOW-001",
                authority=PolicyAuthority.HUMAN_AUTHORITY,
                decision=RuntimeDecision.ALLOW,
            ),
            make_rule(
                rule_id="LAW-HARD-DENY-001",
                authority=PolicyAuthority.MANDATORY_LAW,
                decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            ),
        ]
    )

    assert (
        resolution.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )


def test_empty_policy_set_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At least one policy decision",
    ):
        resolve_policy_decisions([])
