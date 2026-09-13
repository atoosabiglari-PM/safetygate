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
