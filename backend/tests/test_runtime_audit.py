from app.core.audit.runtime_recorder import create_runtime_audit_record
from app.core.authorization.runtime_engine import evaluate_runtime_action
from app.schemas.runtime import (
    ActionProposal,
    HumanApprovalContext,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)


def make_request(
    *,
    risk_level: str = "LOW",
    irreversible: bool = False,
    approval: HumanApprovalContext | None = None,
    passport_status: str = "ACTIVE",
) -> RuntimeAuthorizationRequest:
    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-audit-001",
            agent_id="agent-001",
            agent_version_id="version-001",
            passport_id="passport-001",
            tool_name="deploy_service" if risk_level == "HIGH" else "read_documents",
            action_name="deploy" if risk_level == "HIGH" else "read_document",
            requested_permissions=(
                ["deploy:write"] if risk_level == "HIGH"
                else ["documents:read"]
            ),
            is_irreversible=irreversible,
            risk_level=risk_level,
            evidence={"source": "runtime-test"},
        ),
        passport=PassportContext(
            status=passport_status,
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=["read_documents", "deploy_service"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=["reviewer@example.com"],
        ),
        approval=approval,
    )


def test_allow_decision_creates_audit_record() -> None:
    request = make_request()
    result = evaluate_runtime_action(request)

    record = create_runtime_audit_record(request, result)

    assert result.decision == RuntimeDecision.ALLOW
    assert record.decision == "ALLOW"
    assert record.action_id == "action-audit-001"
    assert record.event_id
    assert record.evidence["source"] == "runtime-test"


def test_human_review_decision_creates_audit_record() -> None:
    request = make_request(
        risk_level="HIGH",
        irreversible=True,
    )
    result = evaluate_runtime_action(request)

    record = create_runtime_audit_record(request, result)

    assert result.decision == RuntimeDecision.HUMAN_REVIEW_REQUIRED
    assert record.decision == "HUMAN_REVIEW_REQUIRED"
    assert record.approval_id is None
    assert record.reasons


def test_human_rejection_creates_deny_audit_record() -> None:
    approval = HumanApprovalContext(
        approval_id="approval-001",
        action_id="action-audit-001",
        approver_identity="reviewer@example.com",
        approved=False,
    )

    request = make_request(
        risk_level="HIGH",
        irreversible=True,
        approval=approval,
    )
    result = evaluate_runtime_action(request)

    record = create_runtime_audit_record(request, result)

    assert result.decision == RuntimeDecision.DENY
    assert record.decision == "DENY"
    assert record.approval_id == "approval-001"
    assert record.approver_identity == "reviewer@example.com"
    assert record.human_approved is False


def test_hard_deny_creates_audit_record() -> None:
    request = make_request(passport_status="REVOKED")
    result = evaluate_runtime_action(request)

    record = create_runtime_audit_record(request, result)

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY
    assert record.decision == "NON_OVERRIDABLE_DENY"
    assert record.passport_status == "REVOKED"
    assert record.reasons


def test_audit_redacts_secrets_but_preserves_useful_evidence() -> None:
    request = make_request()

    request.proposal.evidence = {
        "source": "audit-redaction-test",
        "document_id": "doc-001",
        "api_key": "SUPER-SECRET",
        "nested": {
            "authorization": "Bearer abc123",
            "result_code": "OK",
        },
    }

    result = evaluate_runtime_action(request)
    record = create_runtime_audit_record(request, result)

    assert record.evidence["source"] == "audit-redaction-test"
    assert record.evidence["document_id"] == "doc-001"
    assert record.evidence["api_key"] == "[REDACTED]"
    assert record.evidence["nested"]["authorization"] == "[REDACTED]"
    assert record.evidence["nested"]["result_code"] == "OK"

    serialized = record.model_dump_json()

    assert "SUPER-SECRET" not in serialized
    assert "Bearer abc123" not in serialized
