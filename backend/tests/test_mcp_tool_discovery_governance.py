from app.core.authorization.runtime_engine import (
    evaluate_runtime_action,
)
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)


def _valid_signature(**kwargs) -> bool:
    return True


def _request(
    *,
    passport_tools: list[str],
) -> RuntimeAuthorizationRequest:
    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-mcp-discovery-001",
            agent_id="agent-mcp-001",
            agent_version_id="version-mcp-001",
            passport_id="passport-mcp-001",
            tool_name="server_status",
            action_name="server_status",
            requested_permissions=[],
            is_irreversible=False,
            risk_level="LOW",
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
            allowed_tools=passport_tools,
            conditional_tools=[],
            prohibited_tools=[],
            human_approvers=[],
            issued_at="2026-09-15T00:00:00+00:00",
            signature_key_id="test-key",
            signature="test-signature",
        ),
    )


def test_discovered_tool_is_denied_when_not_in_passport() -> None:
    result = evaluate_runtime_action(
        _request(
            passport_tools=["read_documents"],
        ),
        signature_verifier=_valid_signature,
    )

    assert (
        result.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )

    assert result.reasons == [
        (
            "Tool 'server_status' is not authorized "
            "by the Safety Passport."
        )
    ]


def test_passport_entry_cannot_create_permission_contract() -> None:
    result = evaluate_runtime_action(
        _request(
            passport_tools=[
                "read_documents",
                "server_status",
            ],
        ),
        signature_verifier=_valid_signature,
    )

    assert (
        result.decision
        == RuntimeDecision.NON_OVERRIDABLE_DENY
    )

    assert result.reasons == [
        (
            "Tool 'server_status' has no registered "
            "permission contract."
        )
    ]
