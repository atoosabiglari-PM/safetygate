import app.services.runtime_authorization as runtime_authorization_service
import pytest
from app.core.authorization.execution_store import get_execution_record
from app.core.authorization.runtime_engine import (
    evaluate_runtime_action as _evaluate_runtime_action,
)
from app.core.authorization.tool_gateway import reset_execution_records
from app.db.base import Base
from app.db.session import create_database_engine, create_session_factory
from app.schemas.admission import (
    AdmissionDecision,
    AgentAdmissionRequest,
)
from app.schemas.roles import PrincipalContext, RuntimeRole
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)
from app.schemas.tool_execution import (
    ToolExecutionRequest,
    ToolExecutionStatus,
)
from app.services.governed_workflow import run_governed_workflow


def _valid_signature(**kwargs) -> bool:
    return True


@pytest.fixture(autouse=True)
def _stub_kms_signature_verification(
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


def setup_function() -> None:
    reset_execution_records()


def test_safe_action_runs_end_to_end_and_is_audited(tmp_path) -> None:
    database_path = tmp_path / "governed-workflow.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()

    admission_request = AgentAdmissionRequest(
        agent_name="research-agent",
        owner_identity="owner@example.com",
        purpose="Read approved documents for a test workflow.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-e2e-001",
            agent_id="agent-001",
            agent_version_id="version-001",
            passport_id="passport-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=["documents:read"],
            is_irreversible=False,
            risk_level="LOW",
            evidence={"source": "governed-e2e-test"},
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
            signature_key_id=(
                "projects/safetygate-atoosa-2026/"
                "locations/global/"
                "keyRings/safetygate-dev/"
                "cryptoKeys/safety-passport-signing/"
                "cryptoKeyVersions/1"
            ),
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-e2e-001",
        idempotency_key="idem-e2e-001",
        tool_name="read_documents",
        arguments={"document_id": "safe-test-document"},
    )

    outcome = run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=PrincipalContext(
            identity="reader@example.com",
            roles=[RuntimeRole.READER],
        ),
        session=session,
    )

    assert outcome.admission.decision == AdmissionDecision.PASS

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW
    )

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.EXECUTED

    assert outcome.audit is not None
    assert outcome.audit.action_id == "action-e2e-001"
    assert outcome.audit.decision == "ALLOW"
    assert outcome.audit.execution_outcome == "EXECUTED"
    assert outcome.audit.evidence["source"] == "governed-e2e-test"

    record = get_execution_record(
        session,
        idempotency_key="idem-e2e-001",
    )

    assert record is not None
    assert record.action_id == "action-e2e-001"
    assert record.status == "EXECUTED"
    assert record.result_payload["execution_attempted"] is True

    session.close()
    engine.dispose()


def test_authorized_tool_cannot_be_swapped_before_execution() -> None:
    admission_request = AgentAdmissionRequest(
        agent_name="research-agent",
        owner_identity="owner@example.com",
        purpose="Read approved documents.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-binding-001",
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
            signature_key_id=(
                "projects/safetygate-atoosa-2026/"
                "locations/global/"
                "keyRings/safetygate-dev/"
                "cryptoKeys/safety-passport-signing/"
                "cryptoKeyVersions/1"
            ),
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-binding-001",
        idempotency_key="idem-binding-001",
        tool_name="send_message",
        arguments={
            "recipient": "attacker@example.com",
            "message": "This must never execute.",
        },
    )

    outcome = run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=PrincipalContext(
            identity="reader@example.com",
            roles=[RuntimeRole.READER],
        ),
    )

    assert outcome.authorization is not None
    assert outcome.authorization.decision.decision == RuntimeDecision.ALLOW

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.FAILED_CLOSED
    assert outcome.execution.execution_attempted is False

    assert any(
        "tool_name does not match" in reason
        for reason in outcome.execution.reasons
    )

    assert outcome.audit is not None
    assert outcome.audit.execution_outcome == "FAILED_CLOSED"


def test_conditional_authorization_executes_only_with_verified_conditions() -> None:
    admission_request = AgentAdmissionRequest(
        agent_name="conditional-agent",
        owner_identity="owner@example.com",
        purpose="Read approved documents under conditional controls.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-conditional-001",
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
            allowed_tools=[],
            conditional_tools=["read_documents"],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id=(
                "projects/safetygate-atoosa-2026/"
                "locations/global/"
                "keyRings/safetygate-dev/"
                "cryptoKeys/safety-passport-signing/"
                "cryptoKeyVersions/1"
            ),
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-conditional-001",
        idempotency_key="idem-conditional-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-conditional-001"},
    )

    outcome = run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=PrincipalContext(
            identity="reader@example.com",
            roles=[RuntimeRole.READER],
        ),
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.EXECUTED

    assert outcome.audit is not None
    assert outcome.audit.execution_outcome == "EXECUTED"


def test_conditional_execution_failure_requires_human_review() -> None:
    admission_request = AgentAdmissionRequest(
        agent_name="conditional-agent",
        owner_identity="owner@example.com",
        purpose="Read approved documents under conditional controls.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-conditional-002",
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
            allowed_tools=[],
            conditional_tools=["read_documents"],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id=(
                "projects/safetygate-atoosa-2026/"
                "locations/global/"
                "keyRings/safetygate-dev/"
                "cryptoKeys/safety-passport-signing/"
                "cryptoKeyVersions/1"
            ),
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-conditional-002",
        idempotency_key="idem-conditional-002",
        tool_name="read_documents",
        arguments={},
    )

    outcome = run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=PrincipalContext(
            identity="reader@example.com",
            roles=[RuntimeRole.READER],
        ),
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW_WITH_CONDITIONS
    )

    assert outcome.execution is not None
    assert (
        outcome.execution.status
        == ToolExecutionStatus.HUMAN_REVIEW_REQUIRED
    )
    assert outcome.execution.execution_attempted is False

    assert any(
        "verification requirements" in reason
        for reason in outcome.execution.reasons
    )

    assert outcome.audit is not None
    assert outcome.audit.execution_outcome == "HUMAN_REVIEW_REQUIRED"



def test_reader_role_cannot_execute_send_message() -> None:
    admission_request = AgentAdmissionRequest(
        agent_name="communications-agent",
        owner_identity="owner@example.com",
        purpose="Send approved messages.",
        model_provider="google",
        model_name="gemini",
        tools=["send_message"],
        permissions=["messages:send"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-role-deny-001",
            agent_id="agent-001",
            agent_version_id="version-001",
            passport_id="passport-001",
            tool_name="send_message",
            action_name="send_message",
            requested_permissions=["messages:send"],
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
            allowed_tools=["send_message"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id=(
                "projects/safetygate-atoosa-2026/"
                "locations/global/"
                "keyRings/safetygate-dev/"
                "cryptoKeys/safety-passport-signing/"
                "cryptoKeyVersions/1"
            ),
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-role-deny-001",
        idempotency_key="idem-role-deny-001",
        tool_name="send_message",
        arguments={
            "recipient": "recipient@example.com",
            "message": "This must not execute under the READER role.",
        },
    )

    outcome = run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=PrincipalContext(
            identity="reader@example.com",
            roles=[RuntimeRole.READER],
        ),
    )

    assert outcome.admission.decision == AdmissionDecision.PASS

    assert outcome.authorization is not None
    assert outcome.authorization.decision.decision == RuntimeDecision.ALLOW

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.FAILED_CLOSED
    assert outcome.execution.execution_attempted is False

    assert any(
        "does not hold a role authorized" in reason
        for reason in outcome.execution.reasons
    )

    assert outcome.audit is not None
    assert outcome.audit.execution_outcome == "FAILED_CLOSED"
    assert outcome.audit.principal_identity == "reader@example.com"
    assert outcome.audit.principal_roles == ["READER"]
    assert any(
        "does not hold a role authorized" in reason
        for reason in outcome.audit.enforcement_reasons
    )
