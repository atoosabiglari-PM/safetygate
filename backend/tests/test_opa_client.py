import json

import httpx
import pytest
from app.core.policy.opa_client import (
    OPA_RUNTIME_POLICY_PATH,
    OpaEvaluationError,
    build_opa_runtime_input,
    evaluate_opa_runtime_policy,
)
from app.schemas.runtime import (
    ActionProposal,
    HumanApprovalContext,
    PassportContext,
    RuntimeAuthorizationRequest,
)


def make_request() -> RuntimeAuthorizationRequest:
    return RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-001",
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
            passport_id="passport-001",
            organization_id="org-001",
            agent_version_id="version-001",
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            policy_version="policy-v1",
            risk_class="LOW",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            issued_at="2026-09-13T21:22:26+00:00",
            signature_key_id="kms-version-1",
            signature="signature",
        ),
    )


def test_opa_client_posts_runtime_input_and_returns_rules() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == OPA_RUNTIME_POLICY_PATH

        body = json.loads(request.content)

        assert body == {
            "input": {
                "proposal": {
                    "action_id": "action-001",
                    "tool_name": "read_documents",
                    "risk_level": "LOW",
                    "is_irreversible": False,
                },
                "passport": {
                    "prohibited_tools": ["delete_records"],
                    "human_approvers": [],
                },
                "approval": None,
            }
        }

        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "rule_id": "safetygate.runtime.default_allow",
                        "authority": "ORGANIZATION_POLICY",
                        "source_name": "SafetyGate OPA runtime policy",
                        "source_version": "v1",
                        "source_reference": (
                            "policies/rego/runtime.rego"
                        ),
                        "decision": "ALLOW",
                        "reason": (
                            "OPA policy adds no additional restriction."
                        ),
                        "conditions": [],
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    result = evaluate_opa_runtime_policy(
        make_request(),
        base_url="http://opa.test:8181",
        client=client,
    )

    assert len(result) == 1
    assert result[0]["decision"] == "ALLOW"
    assert (
        result[0]["rule_id"]
        == "safetygate.runtime.default_allow"
    )


def test_opa_client_fails_on_connection_error() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "OPA unavailable.",
            request=request,
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    with pytest.raises(
        OpaEvaluationError,
        match="evaluation failed",
    ):
        evaluate_opa_runtime_policy(
            make_request(),
            base_url="http://opa.test:8181",
            client=client,
        )


def test_opa_client_fails_on_http_error() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            500,
            request=request,
            json={"error": "OPA failure"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    with pytest.raises(
        OpaEvaluationError,
        match="evaluation failed",
    ):
        evaluate_opa_runtime_policy(
            make_request(),
            base_url="http://opa.test:8181",
            client=client,
        )


def test_opa_client_rejects_missing_result() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"unexpected": []},
            )
        )
    )

    with pytest.raises(
        OpaEvaluationError,
        match="did not contain policy decisions",
    ):
        evaluate_opa_runtime_policy(
            make_request(),
            base_url="http://opa.test:8181",
            client=client,
        )


def test_opa_client_rejects_empty_result() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"result": []},
            )
        )
    )

    with pytest.raises(
        OpaEvaluationError,
        match="did not contain policy decisions",
    ):
        evaluate_opa_runtime_policy(
            make_request(),
            base_url="http://opa.test:8181",
            client=client,
        )


def test_opa_client_rejects_non_object_rule() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"result": ["ALLOW"]},
            )
        )
    )

    with pytest.raises(
        OpaEvaluationError,
        match="must be JSON objects",
    ):
        evaluate_opa_runtime_policy(
            make_request(),
            base_url="http://opa.test:8181",
            client=client,
        )



def test_opa_runtime_input_is_minimal_without_approval() -> None:
    opa_input = build_opa_runtime_input(make_request())

    assert opa_input == {
        "proposal": {
            "action_id": "action-001",
            "tool_name": "read_documents",
            "risk_level": "LOW",
            "is_irreversible": False,
        },
        "passport": {
            "prohibited_tools": ["delete_records"],
            "human_approvers": [],
        },
        "approval": None,
    }

    assert "signature" not in opa_input["passport"]
    assert "signature_key_id" not in opa_input["passport"]
    assert "passport_id" not in opa_input["passport"]
    assert "organization_id" not in opa_input["passport"]
    assert "certified_configuration_hash" not in opa_input["passport"]
    assert "current_configuration_hash" not in opa_input["passport"]
    assert "policy_version" not in opa_input["passport"]
    assert "allowed_tools" not in opa_input["passport"]
    assert "conditional_tools" not in opa_input["passport"]

    assert "agent_id" not in opa_input["proposal"]
    assert "agent_version_id" not in opa_input["proposal"]
    assert "passport_id" not in opa_input["proposal"]
    assert "action_name" not in opa_input["proposal"]
    assert "requested_permissions" not in opa_input["proposal"]
    assert "evidence" not in opa_input["proposal"]


def test_opa_runtime_input_maps_only_required_approval_fields() -> None:
    request = make_request().model_copy(
        update={
            "approval": HumanApprovalContext(
                approval_id="approval-001",
                action_id="action-001",
                approver_identity="reviewer@example.com",
                approved=True,
            )
        }
    )

    opa_input = build_opa_runtime_input(request)

    assert opa_input["approval"] == {
        "action_id": "action-001",
        "approver_identity": "reviewer@example.com",
        "approved": True,
    }
    assert "approval_id" not in opa_input["approval"]
