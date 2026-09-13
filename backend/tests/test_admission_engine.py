from app.core.admission.engine import evaluate_admission
from app.schemas.admission import (
    AdmissionDecision,
    AgentAdmissionRequest,
)


def test_low_autonomy_agent_passes() -> None:
    request = AgentAdmissionRequest(
        agent_name="research-agent",
        owner_identity="org-security-team",
        purpose="Read approved documents and summarize them.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    result = evaluate_admission(request)

    assert result.decision == AdmissionDecision.PASS


def test_high_autonomy_without_human_approval_fails() -> None:
    request = AgentAdmissionRequest(
        agent_name="autonomous-agent",
        owner_identity="org-security-team",
        purpose="Perform operational actions.",
        model_provider="google",
        model_name="gemini",
        tools=["deploy_service"],
        permissions=["deploy:write"],
        jurisdictions=["US"],
        autonomy_level="HIGH",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    result = evaluate_admission(request)

    assert result.decision == AdmissionDecision.FAIL
    assert any("human approval" in reason.lower() for reason in result.reasons)


def test_prohibited_tool_conflict_fails() -> None:
    request = AgentAdmissionRequest(
        agent_name="unsafe-agent",
        owner_identity="org-security-team",
        purpose="Test conflicting policy.",
        model_provider="google",
        model_name="gemini",
        tools=["delete_records"],
        permissions=["records:write"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    result = evaluate_admission(request)

    assert result.decision == AdmissionDecision.FAIL
