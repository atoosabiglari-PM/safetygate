from app.core.admission.engine import evaluate_admission
from app.schemas.admission import (
    AdmissionDecision,
    AgentAdmissionRequest,
)


def make_request(**overrides) -> AgentAdmissionRequest:
    data = {
        "agent_name": "research-agent",
        "owner_identity": "org-security-team",
        "purpose": "Read approved documents and summarize them.",
        "model_provider": "google",
        "model_name": "gemini",
        "tools": ["read_documents"],
        "permissions": ["documents:read"],
        "jurisdictions": ["US"],
        "autonomy_level": "LOW",
        "human_approval_actions": [],
        "prohibited_actions": ["delete_records"],
    }

    data.update(overrides)
    return AgentAdmissionRequest(**data)


def test_low_autonomy_agent_passes() -> None:
    result = evaluate_admission(make_request())

    assert result.decision == AdmissionDecision.PASS


def test_high_autonomy_without_human_approval_fails() -> None:
    result = evaluate_admission(
        make_request(
            autonomy_level="HIGH",
            tools=["deploy_service"],
            permissions=["deploy:write"],
        )
    )

    assert result.decision == AdmissionDecision.FAIL
    assert any("human approval" in reason.lower() for reason in result.reasons)


def test_prohibited_capability_is_non_overridable() -> None:
    result = evaluate_admission(
        make_request(
            tools=["delete_records"],
            permissions=["records:write"],
        )
    )

    assert result.decision == AdmissionDecision.NON_OVERRIDABLE_FAIL


def test_missing_jurisdiction_is_non_overridable() -> None:
    result = evaluate_admission(
        make_request(
            jurisdictions=[],
        )
    )

    assert result.decision == AdmissionDecision.NON_OVERRIDABLE_FAIL


def test_non_overridable_failure_takes_precedence() -> None:
    result = evaluate_admission(
        make_request(
            jurisdictions=[],
            autonomy_level="HIGH",
            human_approval_actions=[],
        )
    )

    assert result.decision == AdmissionDecision.NON_OVERRIDABLE_FAIL
    assert len(result.reasons) == 2
