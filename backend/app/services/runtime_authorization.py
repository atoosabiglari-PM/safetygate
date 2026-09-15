from dataclasses import dataclass

from app.core.audit.runtime_recorder import create_runtime_audit_record
from app.core.authorization.runtime_engine import evaluate_runtime_action
from app.core.policy.opa_client import OpaEvaluationError
from app.core.policy.opa_mapper import OpaPolicyMappingError
from app.core.policy.opa_runtime import resolve_opa_runtime_policy
from app.core.policy.resolver import (
    PolicyResolution,
    merge_runtime_and_policy_decision,
)
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)


@dataclass(frozen=True)
class RuntimeAuthorizationOutcome:
    decision: RuntimeDecisionResult
    audit: RuntimeAuditRecord


_TERMINAL_RUNTIME_DENIES = {
    RuntimeDecision.DENY,
    RuntimeDecision.NON_OVERRIDABLE_DENY,
}


def authorize_runtime_action(
    request: RuntimeAuthorizationRequest,
) -> RuntimeAuthorizationOutcome:
    runtime_decision = evaluate_runtime_action(request)

    policy_resolution: PolicyResolution | None = None
    decision = runtime_decision

    # A Python hard deny already prevents execution. OPA cannot weaken it.
    if runtime_decision.decision not in _TERMINAL_RUNTIME_DENIES:
        try:
            policy_resolution = resolve_opa_runtime_policy(
                request
            )
        except (
            OpaEvaluationError,
            OpaPolicyMappingError,
        ):
            decision = RuntimeDecisionResult(
                decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
                reasons=[
                    *runtime_decision.reasons,
                    (
                        "OPA policy evaluation was unavailable "
                        "or invalid; SafetyGate failed closed."
                    ),
                ],
            )
        else:
            decision = merge_runtime_and_policy_decision(
                runtime_result=runtime_decision,
                policy_resolution=policy_resolution,
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
