from datetime import UTC, datetime, timedelta

import jwt
from app.schemas.admission import (
    AdmissionDecision,
    AgentAdmissionRequest,
)
from app.schemas.roles import RuntimeRole
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
from app.services.trusted_workflow import run_oidc_governed_workflow
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://identity.example.com"
AUDIENCE = "safetygate"


def test_verified_oidc_identity_runs_governed_workflow() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "iss": ISSUER,
            "sub": "reader-123",
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "email": "reader@example.com",
            "email_verified": True,
        },
        private_key,
        algorithm="RS256",
    )

    admission_request = AgentAdmissionRequest(
        agent_name="trusted-research-agent",
        owner_identity="owner@example.com",
        purpose="Read approved documents.",
        model_provider="google",
        model_name="gemini",
        tools=["read_documents"],
        permissions=["documents:read"],
        jurisdictions=["US"],
        autonomy_level="LOW",
        human_approval_actions=[],
        prohibited_actions=["delete_records"],
    )

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id="action-trusted-001",
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
            status="ACTIVE",
            certified_configuration_hash="abc123",
            current_configuration_hash="abc123",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
        ),
    )

    tool_request = ToolExecutionRequest(
        action_id="action-trusted-001",
        idempotency_key="idem-trusted-001",
        tool_name="read_documents",
        arguments={
            "document_id": "trusted-document",
        },
    )

    outcome = run_oidc_governed_workflow(
        token=token,
        verification_key=private_key.public_key(),
        issuer=ISSUER,
        audience=AUDIENCE,
        role_assignments={
            (ISSUER, "reader-123"): {
                RuntimeRole.READER,
            }
        },
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
    )

    assert outcome.admission.decision == AdmissionDecision.PASS

    assert outcome.authorization is not None
    assert (
        outcome.authorization.decision.decision
        == RuntimeDecision.ALLOW
    )

    assert outcome.execution is not None
    assert outcome.execution.status == ToolExecutionStatus.EXECUTED

    assert outcome.audit is not None
    assert outcome.audit.principal_identity == (
        f"{ISSUER}|reader-123"
    )
    assert outcome.audit.principal_roles == ["READER"]
