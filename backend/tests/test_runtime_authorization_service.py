import app.services.runtime_authorization as runtime_authorization_service
import pytest
from app.core.authorization.runtime_engine import (
    evaluate_runtime_action as _evaluate_runtime_action,
)
from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.opa_client import OpaEvaluationError
from app.core.policy.opa_mapper import OpaPolicyMappingError
from app.core.policy.resolver import (
    PolicyRuleDecision,
    resolve_policy_decisions,
)
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)
from app.services.runtime_authorization import authorize_runtime_action


def _valid_signature(**kwargs) -> bool:
    return True


def make_policy(
    decision: RuntimeDecision,
    *,
    rule_id: str = "safetygate.runtime.default_allow",
    reason: str = "OPA policy adds no additional restriction.",
    conditions: tuple[str, ...] = (),
):
    return resolve_policy_decisions(
        [
            PolicyRuleDecision(
                provenance=PolicyProvenance(
                    rule_id=rule_id,
                    authority=PolicyAuthority.ORGANIZATION_POLICY,
                    source_name="SafetyGate OPA runtime policy",
                    source_version="v1",
                    source_reference="policies/rego/runtime.rego",
                ),
                decision=decision,
                reason=reason,
                conditions=conditions,
            )
        ]
    )


@pytest.fixture(autouse=True)
def _stub_runtime_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def evaluate_with_test_verifier(
        request: RuntimeAuthorizationRequest,
    ) -> RuntimeDecisionResult:
        return _evaluate_runtime_action(
            request,
            signature_verifier=_valid_signature,
        )

    monkeypatch.setattr(
        runtime_authorization_service,
        "evaluate_runtime_action",
        evaluate_with_test_verifier,
    )

    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        lambda request: make_policy(
            RuntimeDecision.ALLOW
        ),
    )


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
            passport_id="passport-001",
            organization_id="org-001",
            agent_version_id="version-001",
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            policy_version="policy-v1",
            risk_class="LOW",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=[],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id="kms-version-1",
            signature="test-signature",
        ),
    )


def test_authorization_service_returns_decision_and_audit() -> None:
    outcome = authorize_runtime_action(
        make_request()
    )

    assert outcome.decision.decision == RuntimeDecision.ALLOW
    assert outcome.audit.decision == "ALLOW"
    assert outcome.audit.action_id == "action-service-001"
    assert outcome.audit.event_id
    assert outcome.audit.evidence["source"] == "service-test"


def test_audit_matches_runtime_decision() -> None:
    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.audit.decision
        == outcome.decision.decision.value
    )
    assert (
        outcome.audit.reasons
        == outcome.decision.reasons
    )
    assert (
        outcome.audit.conditions
        == outcome.decision.conditions
    )


def test_opa_provenance_is_carried_into_audit() -> None:
    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.audit.policy_rule_id
        == "safetygate.runtime.default_allow"
    )
    assert (
        outcome.audit.policy_authority
        == "ORGANIZATION_POLICY"
    )
    assert (
        outcome.audit.policy_source_name
        == "SafetyGate OPA runtime policy"
    )
    assert outcome.audit.policy_source_version == "v1"
    assert (
        outcome.audit.policy_source_reference
        == "policies/rego/runtime.rego"
    )
    assert len(
        outcome.audit.policy_considered_rules
    ) == 1


def test_opa_can_make_runtime_allow_more_restrictive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        lambda request: make_policy(
            RuntimeDecision.DENY,
            rule_id="safetygate.runtime.policy_deny",
            reason="OPA policy denied the action.",
        ),
    )

    outcome = authorize_runtime_action(
        make_request()
    )

    assert outcome.decision.decision == RuntimeDecision.DENY
    assert (
        outcome.audit.policy_rule_id
        == "safetygate.runtime.policy_deny"
    )


def test_opa_conditions_are_enforced_and_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        lambda request: make_policy(
            RuntimeDecision.ALLOW_WITH_CONDITIONS,
            rule_id="safetygate.runtime.policy_conditions",
            reason="OPA requires additional controls.",
            conditions=(
                "Record enhanced audit evidence.",
            ),
        ),
    )

    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.decision.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )
    assert outcome.decision.conditions == [
        "Record enhanced audit evidence.",
    ]

    considered = (
        outcome.audit.policy_considered_rules[0]
    )

    assert considered["conditions"] == [
        "Record enhanced audit evidence.",
    ]


def test_python_hard_deny_short_circuits_opa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_authorization_service,
        "evaluate_runtime_action",
        lambda request: RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=["Python hard safety boundary."],
        ),
    )

    def opa_must_not_run(
        request: RuntimeAuthorizationRequest,
    ):
        raise AssertionError(
            "OPA must not run after a Python hard deny."
        )

    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        opa_must_not_run,
    )

    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.decision.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )
    assert outcome.audit.policy_rule_id is None



def test_opa_unavailable_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(
        request: RuntimeAuthorizationRequest,
    ):
        raise OpaEvaluationError("OPA unavailable.")

    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        unavailable,
    )

    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.decision.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )
    assert outcome.audit.decision == "NON_OVERRIDABLE_DENY"
    assert outcome.audit.policy_rule_id is None

    assert any(
        "SafetyGate failed closed" in reason
        for reason in outcome.decision.reasons
    )


def test_invalid_opa_policy_output_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_policy(
        request: RuntimeAuthorizationRequest,
    ):
        raise OpaPolicyMappingError(
            "Unknown OPA runtime decision: MAYBE"
        )

    monkeypatch.setattr(
        runtime_authorization_service,
        "resolve_opa_runtime_policy",
        invalid_policy,
    )

    outcome = authorize_runtime_action(
        make_request()
    )

    assert (
        outcome.decision.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )
    assert outcome.audit.decision == "NON_OVERRIDABLE_DENY"
    assert outcome.audit.policy_rule_id is None

    assert any(
        "SafetyGate failed closed" in reason
        for reason in outcome.decision.reasons
    )
