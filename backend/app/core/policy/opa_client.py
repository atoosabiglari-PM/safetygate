from typing import Any

import httpx

from app.schemas.runtime import RuntimeAuthorizationRequest

OPA_RUNTIME_POLICY_PATH = (
    "/v1/data/safetygate/runtime/rule_decisions"
)


class OpaEvaluationError(RuntimeError):
    """Raised when OPA cannot return a usable policy result."""


def build_opa_runtime_input(
    request: RuntimeAuthorizationRequest,
) -> dict[str, Any]:
    approval: dict[str, Any] | None = None

    if request.approval is not None:
        approval = {
            "action_id": request.approval.action_id,
            "approver_identity": request.approval.approver_identity,
            "approved": request.approval.approved,
        }

    return {
        "proposal": {
            "action_id": request.proposal.action_id,
            "tool_name": request.proposal.tool_name,
            "risk_level": request.proposal.risk_level,
            "is_irreversible": request.proposal.is_irreversible,
        },
        "passport": {
            "prohibited_tools": list(request.passport.prohibited_tools),
            "human_approvers": list(request.passport.human_approvers),
        },
        "approval": approval,
    }


def evaluate_opa_runtime_policy(
    request: RuntimeAuthorizationRequest,
    *,
    base_url: str,
    timeout_seconds: float = 2.0,
    client: httpx.Client | None = None,
) -> tuple[dict[str, Any], ...]:
    if not base_url.strip():
        raise ValueError("OPA base URL is required.")

    if timeout_seconds <= 0:
        raise ValueError("OPA timeout must be greater than zero.")

    url = (
        base_url.rstrip("/")
        + OPA_RUNTIME_POLICY_PATH
    )

    payload = {
        "input": build_opa_runtime_input(request),
    }

    owns_client = client is None
    http_client = client or httpx.Client()

    try:
        response = http_client.post(
            url,
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpaEvaluationError(
            "OPA runtime policy evaluation failed."
        ) from exc
    finally:
        if owns_client:
            http_client.close()

    try:
        body = response.json()
    except ValueError as exc:
        raise OpaEvaluationError(
            "OPA returned invalid JSON."
        ) from exc

    if not isinstance(body, dict):
        raise OpaEvaluationError(
            "OPA response must be a JSON object."
        )

    result = body.get("result")

    if not isinstance(result, list) or not result:
        raise OpaEvaluationError(
            "OPA response did not contain policy decisions."
        )

    if not all(isinstance(item, dict) for item in result):
        raise OpaEvaluationError(
            "OPA policy decisions must be JSON objects."
        )

    return tuple(dict(item) for item in result)
