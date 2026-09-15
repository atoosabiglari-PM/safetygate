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
from app.schemas.admission import AgentAdmissionRequest
from app.schemas.roles import PrincipalContext, RuntimeRole
from app.schemas.runtime import PassportContext, RuntimeDecision
from app.schemas.tool_execution import ToolExecutionStatus


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
        agent_name="agent-runtime-test",
        owner_identity="owner@example.com",
        purpose="Read certified documents.",
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
        passport_id="passport-agent-001",
        organization_id="org-agent-001",
        agent_version_id="version-agent-001",
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


def test_agent_proposal_reaches_executor_only_after_authorization() -> None:
    calls = []

    def executor(tool_name, arguments):
        calls.append(
            (tool_name, arguments)
        )
        return {
            "transport": "mcp",
            "document_id": arguments["document_id"],
        }

    outcome = run_agent_proposal(
        proposal=AgentToolProposal(
            action_id="action-agent-001",
            agent_id="agent-001",
            agent_version_id="version-agent-001",
            tool_name="read_documents",
            action_name="read_document",
            requested_permissions=("documents:read",),
            arguments={
                "document_id": "doc-001",
            },
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
    assert outcome.execution.status == ToolExecutionStatus.EXECUTED

    assert calls == [
        (
            "read_documents",
            {
                "document_id": "doc-001",
            },
        )
    ]


def test_agent_cannot_escalate_to_uncertified_tool() -> None:
    def forbidden_executor(tool_name, arguments):
        raise AssertionError(
            "Executor must not run for uncertified agent proposal."
        )

    outcome = run_agent_proposal(
        proposal=AgentToolProposal(
            action_id="action-agent-002",
            agent_id="agent-001",
            agent_version_id="version-agent-001",
            tool_name="server_status",
            action_name="server_status",
            requested_permissions=(),
            arguments={},
        ),
        admission_request=_admission(),
        passport=_passport(),
        principal=_principal(),
        tool_executor=forbidden_executor,
    )

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )

    assert outcome.execution is None
