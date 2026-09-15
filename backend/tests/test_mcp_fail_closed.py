import sys
from pathlib import Path

import app.services.runtime_authorization as runtime_authorization_service
import pytest
from app.core.authorization.runtime_engine import (
    evaluate_runtime_action as _evaluate_runtime_action,
)
from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.resolver import (
    PolicyRuleDecision,
    resolve_policy_decisions,
)
from app.integrations.agent_bridge import (
    AgentToolProposal,
    run_agent_proposal,
)
from app.integrations.mcp_client import McpStdioServerConfig
from app.integrations.mcp_executor import build_stdio_mcp_executor
from app.schemas.admission import AgentAdmissionRequest
from app.schemas.roles import PrincipalContext, RuntimeRole
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


def _valid_signature(**kwargs) -> bool:
    return True


def _allow_opa_policy():
    return resolve_policy_decisions(
        [
            PolicyRuleDecision(
                provenance=PolicyProvenance(
                    rule_id="safetygate.runtime.default_allow",
                    authority=PolicyAuthority.ORGANIZATION_POLICY,
                    source_name="SafetyGate OPA runtime policy",
                    source_version="v1",
                    source_reference="policies/rego/runtime.rego",
                ),
                decision=RuntimeDecision.ALLOW,
                reason="OPA policy adds no additional restriction.",
            )
        ]
    )


@pytest.fixture(autouse=True)
def _runtime_test_seams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def evaluate_with_test_verifier(request):
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
        lambda request: _allow_opa_policy(),
    )


def _admission() -> AgentAdmissionRequest:
    return AgentAdmissionRequest(
        agent_name="mcp-adversarial-test-agent",
        owner_identity="owner@example.com",
        purpose="Read certified documents through SafetyGate.",
        model_provider="test",
        model_name="test-agent",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )


def _passport() -> PassportContext:
    return PassportContext(
        passport_id="passport-mcp-adversarial-001",
        organization_id="org-test-001",
        agent_version_id="version-mcp-adversarial-001",
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
    )


def _principal() -> PrincipalContext:
    return PrincipalContext(
        identity="reader@example.com",
        roles=[RuntimeRole.READER],
    )


def test_uncertified_discovered_tool_never_reaches_executor() -> None:
    calls = []

    def executor(tool_name, arguments):
        calls.append((tool_name, arguments))
        raise AssertionError(
            "Uncertified MCP tool must never execute."
        )

    outcome = run_agent_proposal(
        proposal=AgentToolProposal(
            action_id="attack-uncertified-test-001",
            agent_id="agent-test-001",
            agent_version_id="version-mcp-adversarial-001",
            tool_name="server_status",
            action_name="server_status",
            requested_permissions=(),
            arguments={},
        ),
        admission_request=_admission(),
        passport=_passport(),
        principal=_principal(),
        tool_executor=executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )
    assert outcome.execution is None
    assert calls == []


def test_tool_swap_after_authorization_never_reaches_executor() -> None:
    calls = []

    def executor(tool_name, arguments):
        calls.append((tool_name, arguments))
        raise AssertionError(
            "Swapped MCP tool must never execute."
        )

    passport = _passport()

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="attack-swap-test-001",
            agent_id="agent-test-001",
            agent_version_id="version-mcp-adversarial-001",
            passport_id=passport.passport_id,
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=["documents:read"],
            is_irreversible=False,
            risk_level="LOW",
            evidence={
                "source": "step-11.8-tool-swap",
            },
        ),
        passport=passport,
    )

    tool_request = ToolExecutionRequest(
        action_id="attack-swap-test-001",
        idempotency_key="attack:swap:test:001",
        tool_name="server_status",
        arguments={},
    )

    outcome = run_governed_workflow(
        admission_request=_admission(),
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=_principal(),
        tool_executor=executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW
    )

    assert outcome.execution is not None
    assert (
        outcome.execution.status
        == ToolExecutionStatus.FAILED_CLOSED
    )
    assert outcome.execution.execution_attempted is False
    assert calls == []

    assert any(
        "tool_name does not match" in reason
        for reason in outcome.execution.reasons
    )


def test_invalid_arguments_never_reach_executor() -> None:
    calls = []

    def executor(tool_name, arguments):
        calls.append((tool_name, arguments))
        raise AssertionError(
            "Invalid MCP arguments must never execute."
        )

    outcome = run_agent_proposal(
        proposal=AgentToolProposal(
            action_id="attack-invalid-args-test-001",
            agent_id="agent-test-001",
            agent_version_id="version-mcp-adversarial-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=("documents:read",),
            arguments={},
        ),
        admission_request=_admission(),
        passport=_passport(),
        principal=_principal(),
        tool_executor=executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW
    )

    assert outcome.execution is not None
    assert (
        outcome.execution.status
        == ToolExecutionStatus.FAILED_CLOSED
    )
    assert outcome.execution.execution_attempted is False
    assert calls == []


def test_real_mcp_failure_fails_closed_and_is_audited(
    tmp_path: Path,
) -> None:
    real_executor = build_stdio_mcp_executor(
        McpStdioServerConfig(
            command=sys.executable,
            args=(
                "-m",
                "app.integrations.mcp_servers.document_server",
            ),
            env=(
                (
                    "SAFETYGATE_DOCUMENT_ROOT",
                    str(tmp_path),
                ),
            ),
        )
    )

    calls = []

    def counted_executor(tool_name, arguments):
        calls.append((tool_name, arguments))
        return real_executor(
            tool_name,
            arguments,
        )

    outcome = run_agent_proposal(
        proposal=AgentToolProposal(
            action_id="attack-real-mcp-failure-test-001",
            agent_id="agent-test-001",
            agent_version_id="version-mcp-adversarial-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=("documents:read",),
            arguments={
                "document_id": "document-that-does-not-exist",
            },
        ),
        admission_request=_admission(),
        passport=_passport(),
        principal=_principal(),
        tool_executor=counted_executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW
    )

    assert outcome.execution is not None
    assert (
        outcome.execution.status
        == ToolExecutionStatus.FAILED_CLOSED
    )
    assert outcome.execution.execution_attempted is True

    assert calls == [
        (
            "read_documents",
            {
                "document_id": "document-that-does-not-exist",
            },
        )
    ]

    assert outcome.audit is not None
    assert (
        outcome.audit.execution_outcome
        == ToolExecutionStatus.FAILED_CLOSED.value
    )
