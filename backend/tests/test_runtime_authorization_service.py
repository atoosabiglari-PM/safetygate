from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.resolver import (
    PolicyRuleDecision,
    resolve_policy_decisions,
)
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)
from app.services.runtime_authorization import authorize_runtime_action


def make_request() -> RuntimeAuthorizationRequest:
    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-service-001",
            agent_id="agent-001",
            agent_version_id="version-001",
            passport_id="passport-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=["documents:read"],
            is_irreversible=False,
            risk_level="LOW",
            evidence={"source": "service-test"},
        ),
        passport=PassportContext(
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=[],
            human_approvers=[],
        ),
    )


def test_authorization_service_returns_decision_and_audit() -> None:
    outcome = authorize_runtime_action(make_request())

    assert outcome.decision.decision == RuntimeDecision.ALLOW
    assert outcome.audit.decision == "ALLOW"
    assert outcome.audit.action_id == "action-service-001"
    assert outcome.audit.event_id
    assert outcome.audit.evidence["source"] == "service-test"


def test_audit_matches_runtime_decision() -> None:
    outcome = authorize_runtime_action(make_request())

    assert outcome.audit.decision == outcome.decision.decision.value
    assert outcome.audit.reasons == outcome.decision.reasons
    assert outcome.audit.conditions == outcome.decision.conditions


def test_authorization_service_carries_policy_provenance_into_audit() -> None:
    policy_resolution = resolve_policy_decisions(
        [
            PolicyRuleDecision(
                provenance=PolicyProvenance(
                    rule_id="ORG-ALLOW-001",
                    authority=PolicyAuthority.ORGANIZATION_POLICY,
                    source_name="Organization Policy",
                    source_version="2026-09",
                    source_reference="policy/runtime-read",
                ),
                decision=RuntimeDecision.ALLOW,
                reason="Organization policy permits the read action.",
            )
        ]
    )

    outcome = authorize_runtime_action(
        make_request(),
        policy_resolution=policy_resolution,
    )

    assert outcome.decision.decision == RuntimeDecision.ALLOW
    assert outcome.audit.policy_rule_id == "ORG-ALLOW-001"
    assert outcome.audit.policy_authority == "ORGANIZATION_POLICY"
    assert outcome.audit.policy_source_name == "Organization Policy"
    assert outcome.audit.policy_source_version == "2026-09"
    assert outcome.audit.policy_source_reference == "policy/runtime-read"
    assert len(outcome.audit.policy_considered_rules) == 1

def test_authorization_service_rejects_inconsistent_policy_resolution() -> None:
    policy_resolution = resolve_policy_decisions(
        [
            PolicyRuleDecision(
                provenance=PolicyProvenance(
                    rule_id="ORG-DENY-001",
                    authority=PolicyAuthority.ORGANIZATION_POLICY,
                    source_name="Organization Policy",
                    source_version="2026-09",
                    source_reference="policy/runtime-read",
                ),
                decision=RuntimeDecision.DENY,
                reason="Organization policy denies the action.",
            )
        ]
    )

    try:
        authorize_runtime_action(
            make_request(),
            policy_resolution=policy_resolution,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError(
            "Inconsistent policy resolution did not fail closed."
        )
