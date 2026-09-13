from dataclasses import dataclass

from app.core.audit.runtime_recorder import create_runtime_audit_record
from app.core.authorization.runtime_engine import evaluate_runtime_action
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
) -> RuntimeAuthorizationOutcome:
    decision = evaluate_runtime_action(request)

    audit = create_runtime_audit_record(
        request=request,
        result=decision,
    )

    return RuntimeAuthorizationOutcome(
        decision=decision,
        audit=audit,
    )
