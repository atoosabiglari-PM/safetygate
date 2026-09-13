from dataclasses import dataclass

from app.core.audit.runtime_recorder import create_runtime_audit_record
from app.core.authorization.runtime_engine import evaluate_runtime_action
from app.core.policy.resolver import PolicyResolution
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecisionResult,
)


@dataclass(frozen=True)
class RuntimeAuthorizationOutcome:
    decision: RuntimeDecisionResult
    audit: RuntimeAuditRecord


def authorize_runtime_action(
    request: RuntimeAuthorizationRequest,
    *,
    policy_resolution: PolicyResolution | None = None,
) -> RuntimeAuthorizationOutcome:
    decision = evaluate_runtime_action(request)

    if (
        policy_resolution is not None
        and policy_resolution.decision != decision.decision
    ):
        raise ValueError(
            "Policy resolution decision does not match "
            "runtime authorization decision."
        )

    audit = create_runtime_audit_record(
        request=request,
        result=decision,
        policy_resolution=policy_resolution,
    )

    return RuntimeAuthorizationOutcome(
        decision=decision,
        audit=audit,
    )
