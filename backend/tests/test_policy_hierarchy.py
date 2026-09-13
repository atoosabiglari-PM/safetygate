from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
    higher_authority,
)


def test_mandatory_law_outranks_organization_policy() -> None:
    winner = higher_authority(
        PolicyAuthority.MANDATORY_LAW,
        PolicyAuthority.ORGANIZATION_POLICY,
    )

    assert winner == PolicyAuthority.MANDATORY_LAW


def test_human_authority_cannot_outrank_security_standard() -> None:
    winner = higher_authority(
        PolicyAuthority.HUMAN_AUTHORITY,
        PolicyAuthority.SECURITY_STANDARD,
    )

    assert winner == PolicyAuthority.SECURITY_STANDARD


def test_policy_provenance_preserves_rule_source() -> None:
    provenance = PolicyProvenance(
        rule_id="SEC-001",
        authority=PolicyAuthority.SECURITY_STANDARD,
        source_name="SafetyGate Security Baseline",
        source_version="2026-09",
        source_reference="controls/tool-execution",
    )

    assert provenance.rule_id == "SEC-001"
    assert provenance.authority == PolicyAuthority.SECURITY_STANDARD
    assert provenance.source_name == "SafetyGate Security Baseline"
    assert provenance.source_version == "2026-09"
    assert provenance.source_reference == "controls/tool-execution"
