from app.core.authorization.runtime_engine import evaluate_runtime_action
from app.schemas.runtime import ActionProposal, RuntimeDecision


def make_proposal(**overrides) -> ActionProposal:
    data = {
        "agent_id": "agent-001",
        "agent_version_id": "version-001",
        "passport_id": "passport-001",
        "tool_name": "read_documents",
        "action_name": "read_document",
        "requested_permissions": ["documents:read"],
        "is_irreversible": False,
        "risk_level": "LOW",
        "evidence": {},
    }

    data.update(overrides)
    return ActionProposal(**data)


def test_low_risk_valid_action_is_allowed() -> None:
    result = evaluate_runtime_action(make_proposal())

    assert result.decision == RuntimeDecision.ALLOW


def test_unknown_tool_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_proposal(tool_name="mystery_tool")
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_missing_permission_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_proposal(
            tool_name="send_message",
            requested_permissions=["documents:read"],
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_prohibited_tool_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_proposal(
            tool_name="delete_records",
            requested_permissions=["records:delete"],
            risk_level="HIGH",
            is_irreversible=True,
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_high_risk_irreversible_action_requires_human_review() -> None:
    result = evaluate_runtime_action(
        make_proposal(
            tool_name="deploy_service",
            requested_permissions=["deploy:write"],
            risk_level="HIGH",
            is_irreversible=True,
        )
    )

    assert result.decision == RuntimeDecision.HUMAN_REVIEW_REQUIRED


def test_medium_risk_action_is_allowed_with_conditions() -> None:
    result = evaluate_runtime_action(
        make_proposal(
            tool_name="send_message",
            requested_permissions=["messages:send"],
            risk_level="MEDIUM",
        )
    )

    assert result.decision == RuntimeDecision.ALLOW_WITH_CONDITIONS
    assert len(result.conditions) == 2
