import pytest
from app.core.policy import opa_runtime
from app.core.policy.opa_client import OpaEvaluationError
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)


def make_request() -> RuntimeAuthorizationRequest:
    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-opa-runtime-001",
            agent_id="agent-001",
            agent_version_id="version-001",
            passport_id="passport-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=["documents:read"],
            is_irreversible=False,
            risk_level="LOW",
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
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id="kms-version-1",
            signature="test-signature",
        ),
    )


def test_missing_opa_url_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        opa_runtime.OPA_BASE_URL_ENV,
        raising=False,
    )

    with pytest.raises(
        OpaEvaluationError,
        match="not configured",
    ):
        opa_runtime.resolve_opa_runtime_policy(
            make_request()
        )


def test_configured_opa_result_is_mapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        opa_runtime.OPA_BASE_URL_ENV,
        "http://opa.test:8181",
    )

    def fake_evaluate(
        request: RuntimeAuthorizationRequest,
        *,
        base_url: str,
    ):
        assert base_url == "http://opa.test:8181"

        return (
            {
                "rule_id": "safetygate.runtime.default_allow",
                "authority": "ORGANIZATION_POLICY",
                "source_name": "SafetyGate OPA runtime policy",
                "source_version": "v1",
                "source_reference": "policies/rego/runtime.rego",
                "decision": "ALLOW",
                "reason": "OPA policy adds no additional restriction.",
                "conditions": [],
            },
        )

    monkeypatch.setattr(
        opa_runtime,
        "evaluate_opa_runtime_policy",
        fake_evaluate,
    )

    resolution = opa_runtime.resolve_opa_runtime_policy(
        make_request()
    )

    assert resolution.decision == RuntimeDecision.ALLOW
    assert (
        resolution.winning_rule.provenance.rule_id
        == "safetygate.runtime.default_allow"
    )
