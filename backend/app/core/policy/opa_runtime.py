import os

from app.core.policy.opa_client import (
    OpaEvaluationError,
    evaluate_opa_runtime_policy,
)
from app.core.policy.opa_mapper import (
    build_policy_resolution_from_opa,
)
from app.core.policy.resolver import PolicyResolution
from app.schemas.runtime import RuntimeAuthorizationRequest

OPA_BASE_URL_ENV = "SAFETYGATE_OPA_URL"


def resolve_opa_runtime_policy(
    request: RuntimeAuthorizationRequest,
) -> PolicyResolution:
    base_url = os.getenv(
        OPA_BASE_URL_ENV,
        "",
    ).strip()

    if not base_url:
        raise OpaEvaluationError(
            "SafetyGate OPA runtime policy endpoint "
            "is not configured."
        )

    rules = evaluate_opa_runtime_policy(
        request,
        base_url=base_url,
    )

    return build_policy_resolution_from_opa(
        rules
    )
