from app.core.authorization.runtime_engine import evaluate_runtime_action
from app.schemas.runtime import (
    ActionProposal,
    HumanApprovalContext,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)


def make_request(
    proposal_overrides=None,
    passport_overrides=None,
    approval_overrides=None,
) -> RuntimeAuthorizationRequest:
    proposal_data = {
        "action_id": "action-001",
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

    passport_data = {
        "status": "ACTIVE",
        "certified_configuration_hash": "abc123",
        "current_configuration_hash": "abc123",
        "allowed_tools": ["read_documents", "deploy_service"],
        "conditional_tools": ["send_message"],
        "prohibited_tools": ["delete_records"],
        "human_approvers": ["reviewer@example.com"],
    }

    if proposal_overrides:
        proposal_data.update(proposal_overrides)

    if passport_overrides:
        passport_data.update(passport_overrides)

    approval = None

    if approval_overrides is not None:
        approval_data = {
            "approval_id": "approval-001",
            "action_id": proposal_data["action_id"],
            "approver_identity": "reviewer@example.com",
            "approved": True,
        }
        approval_data.update(approval_overrides)
        approval = HumanApprovalContext(**approval_data)

    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(**proposal_data),
        passport=PassportContext(**passport_data),
        approval=approval,
    )


def test_valid_low_risk_action_is_allowed() -> None:
    result = evaluate_runtime_action(make_request())

    assert result.decision == RuntimeDecision.ALLOW


def test_inactive_passport_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            passport_overrides={
                "status": "REVOKED",
            }
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_configuration_mismatch_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            passport_overrides={
                "current_configuration_hash": "changed456",
            }
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY
    assert any(
        "configuration" in reason.lower()
        for reason in result.reasons
    )


def test_tool_not_in_passport_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "mystery_tool",
            }
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_prohibited_passport_tool_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "delete_records",
                "requested_permissions": ["records:delete"],
            }
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_missing_permission_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "send_message",
                "requested_permissions": ["documents:read"],
            }
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY
    assert any(
        "messages:send" in reason
        for reason in result.reasons
    )


def test_conditional_passport_tool_is_allowed_with_conditions() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "send_message",
                "requested_permissions": ["messages:send"],
            }
        )
    )

    assert result.decision == RuntimeDecision.ALLOW_WITH_CONDITIONS
    assert len(result.conditions) == 2


def test_high_risk_irreversible_without_approval_requires_review() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "deploy_service",
                "requested_permissions": ["deploy:write"],
                "risk_level": "HIGH",
                "is_irreversible": True,
            }
        )
    )

    assert result.decision == RuntimeDecision.HUMAN_REVIEW_REQUIRED


def test_high_risk_irreversible_with_valid_approval_is_allowed() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "deploy_service",
                "requested_permissions": ["deploy:write"],
                "risk_level": "HIGH",
                "is_irreversible": True,
            },
            approval_overrides={},
        )
    )

    assert result.decision == RuntimeDecision.ALLOW


def test_mismatched_action_approval_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "deploy_service",
                "requested_permissions": ["deploy:write"],
                "risk_level": "HIGH",
                "is_irreversible": True,
            },
            approval_overrides={
                "action_id": "different-action",
            },
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_unauthorized_approver_is_non_overridable_denied() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "deploy_service",
                "requested_permissions": ["deploy:write"],
                "risk_level": "HIGH",
                "is_irreversible": True,
            },
            approval_overrides={
                "approver_identity": "attacker@example.com",
            },
        )
    )

    assert result.decision == RuntimeDecision.NON_OVERRIDABLE_DENY


def test_authorized_human_rejection_denies_action() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "tool_name": "deploy_service",
                "requested_permissions": ["deploy:write"],
                "risk_level": "HIGH",
                "is_irreversible": True,
            },
            approval_overrides={
                "approved": False,
            },
        )
    )

    assert result.decision == RuntimeDecision.DENY


def test_medium_risk_allowed_tool_requires_conditions() -> None:
    result = evaluate_runtime_action(
        make_request(
            proposal_overrides={
                "risk_level": "MEDIUM",
            }
        )
    )

    assert result.decision == RuntimeDecision.ALLOW_WITH_CONDITIONS
