from app.core.authorization.tool_gateway import reset_execution_records
from app.schemas.admission import (
    AdmissionDecision,
    AgentAdmissionRequest,
)
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)
from app.schemas.tool_execution import (
    ToolExecutionRequest,
    ToolExecutionStatus,
)
from app.services.governed_workflow import run_governed_workflow


def setup_function() -> None:
    reset_execution_records()


def test_safe_action_runs_end_to_end_and_is_audited() -> None:
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
            evidence={"source": "week5-e2e-test"},
        ),
        passport=PassportContext(
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
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
    assert outcome.audit.evidence["source"] == "week5-e2e-test"


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
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
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
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=[],
            conditional_tools=["read_documents"],
            prohibited_tools=["delete_records"],
            human_approvers=[],
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
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=[],
            conditional_tools=["read_documents"],
            prohibited_tools=["delete_records"],
            human_approvers=[],
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
