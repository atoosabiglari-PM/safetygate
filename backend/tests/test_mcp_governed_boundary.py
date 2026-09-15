import app.integrations.mcp_executor as mcp_executor_module
import pytest
from app.core.audit.runtime_recorder import create_runtime_audit_record
from app.core.authorization.tool_gateway import reset_execution_records
from app.integrations.mcp_client import McpStdioServerConfig
from app.schemas.admission import (
    AdmissionDecision,
    AdmissionResult,
    AgentAdmissionRequest,
)
from app.schemas.roles import (
    PrincipalContext,
    RoleAuthorizationResult,
    RoleDecision,
    RuntimeRole,
)
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)
from app.schemas.tool_execution import ToolExecutionRequest, ToolExecutionStatus
from app.services import governed_workflow
from app.services.runtime_authorization import RuntimeAuthorizationOutcome


@pytest.fixture(autouse=True)
def _reset_execution_records() -> None:
    reset_execution_records()


def _build_inputs():
    admission_request = AgentAdmissionRequest(
        agent_name="mcp-research-agent",
        owner_identity="owner@example.com",
        purpose="Read certified documents through MCP.",
        model_provider="test",
        model_name="test-agent",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-mcp-boundary-001",
            agent_id="agent-mcp-001",
            agent_version_id="version-mcp-001",
            passport_id="passport-mcp-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=["documents:read"],
            is_irreversible=False,
            risk_level="LOW",
            evidence={"source": "mcp-boundary-test"},
        ),
        passport=PassportContext(
            passport_id="passport-mcp-001",
            organization_id="org-mcp-001",
            agent_version_id="version-mcp-001",
            status="ACTIVE",
            certified_configuration_hash="config-hash",
            current_configuration_hash="config-hash",
            policy_version="policy-v1",
            risk_class="LOW",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-15T00:00:00+00:00",
            signature_key_id="test-key",
            signature="test-signature",
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-mcp-boundary-001",
        idempotency_key="idem-mcp-boundary-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-001"},
    )

    principal = PrincipalContext(
        identity="reader@example.com",
        roles=[RuntimeRole.READER],
    )

    return (
        admission_request,
        runtime_request,
        tool_request,
        principal,
    )


def _authorization(
    request: RuntimeAuthorizationRequest,
    decision: RuntimeDecision,
) -> RuntimeAuthorizationOutcome:
    result = RuntimeDecisionResult(
        decision=decision,
        reasons=["Boundary test decision."],
    )

    audit = create_runtime_audit_record(
        request=request,
        result=result,
        policy_resolution=None,
    )

    return RuntimeAuthorizationOutcome(
        decision=result,
        audit=audit,
    )


def _prepare_governance(
    monkeypatch: pytest.MonkeyPatch,
    *,
    decision: RuntimeDecision,
) -> None:
    monkeypatch.setattr(
        governed_workflow,
        "evaluate_admission",
        lambda request: AdmissionResult(
            decision=AdmissionDecision.PASS,
            reasons=[],
        ),
    )

    monkeypatch.setattr(
        governed_workflow,
        "authorize_runtime_action",
        lambda request: _authorization(
            request,
            decision,
        ),
    )

    monkeypatch.setattr(
        governed_workflow,
        "authorize_role",
        lambda request: RoleAuthorizationResult(
            decision=RoleDecision.ALLOW,
            reasons=[],
        ),
    )


def test_stdio_mcp_executor_calls_real_adapter_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeAdapter:
        def __init__(self, config):
            captured["config"] = config

        async def call_tool(self, tool_name, arguments):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments

            return {
                "structured_content": {
                    "document_id": arguments["document_id"],
                },
                "content": [],
            }

    monkeypatch.setattr(
        mcp_executor_module,
        "McpStdioClientAdapter",
        FakeAdapter,
    )

    config = McpStdioServerConfig(
        command="python",
        args=("-m", "test.server"),
    )

    executor = mcp_executor_module.build_stdio_mcp_executor(
        config
    )

    result = executor(
        "read_documents",
        {"document_id": "doc-001"},
    )

    assert captured["config"] == config
    assert captured["tool_name"] == "read_documents"
    assert captured["arguments"] == {
        "document_id": "doc-001",
    }
    assert result["structured_content"]["document_id"] == "doc-001"


def test_governed_allow_invokes_tool_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_governance(
        monkeypatch,
        decision=RuntimeDecision.ALLOW,
    )

    (
        admission_request,
        runtime_request,
        tool_request,
        principal,
    ) = _build_inputs()

    calls = []

    def mcp_executor(tool_name, arguments):
        calls.append(
            (tool_name, arguments)
        )

        return {
            "transport": "mcp",
            "document_id": arguments["document_id"],
        }

    outcome = governed_workflow.run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=principal,
        tool_executor=mcp_executor,
    )

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.EXECUTED

    assert calls == [
        (
            "read_documents",
            {"document_id": "doc-001"},
        )
    ]

    assert outcome.execution.output == {
        "transport": "mcp",
        "document_id": "doc-001",
    }


def test_governed_deny_never_invokes_tool_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_governance(
        monkeypatch,
        decision=RuntimeDecision.DENY,
    )

    (
        admission_request,
        runtime_request,
        tool_request,
        principal,
    ) = _build_inputs()

    def forbidden_executor(tool_name, arguments):
        raise AssertionError(
            "MCP executor must never run after SafetyGate DENY."
        )

    outcome = governed_workflow.run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=principal,
        tool_executor=forbidden_executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.DENY
    )

    assert outcome.execution is None
