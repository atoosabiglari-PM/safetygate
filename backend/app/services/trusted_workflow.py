from collections.abc import Collection, Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.core.identity.oidc import verify_oidc_token
from app.core.identity.principal import (
    RoleAssignmentKey,
    build_verified_principal,
)
from app.schemas.admission import AgentAdmissionRequest
from app.schemas.roles import RuntimeRole
from app.schemas.runtime import RuntimeAuthorizationRequest
from app.schemas.tool_execution import ToolExecutionRequest
from app.services.governed_workflow import (
    GovernedWorkflowOutcome,
    run_governed_workflow,
)


def run_oidc_governed_workflow(
    *,
    token: str,
    verification_key: Any,
    issuer: str,
    audience: str,
    role_assignments: Mapping[
        RoleAssignmentKey,
        Collection[RuntimeRole],
    ],
    admission_request: AgentAdmissionRequest,
    runtime_request: RuntimeAuthorizationRequest,
    tool_request: ToolExecutionRequest,
    session: Session | None = None,
    algorithm: str = "RS256",
) -> GovernedWorkflowOutcome:
    identity = verify_oidc_token(
        token=token,
        verification_key=verification_key,
        issuer=issuer,
        audience=audience,
        algorithm=algorithm,
    )

    principal = build_verified_principal(
        identity=identity,
        role_assignments=role_assignments,
    )

    return run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=principal,
        session=session,
    )
