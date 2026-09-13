from dataclasses import dataclass

from app.core.authorization.failure_policy import evaluate_failure_policy
from app.schemas.failure import (
    ExecutionFailureContext,
    FailureDisposition,
    FailureType,
)


class TransientToolError(RuntimeError):
    pass


class PartialToolFailure(RuntimeError):
    pass


SAFE_AUTO_RETRY_TOOLS = {"read_documents"}


@dataclass(frozen=True)
class ExecutionFailureDecision:
    failure_type: FailureType
    disposition: FailureDisposition


def classify_execution_failure(
    error: Exception,
) -> FailureType:
    if isinstance(error, TimeoutError):
        return FailureType.TIMEOUT

    if isinstance(error, TransientToolError):
        return FailureType.TRANSIENT

    if isinstance(error, PartialToolFailure):
        return FailureType.PARTIAL_FAILURE

    return FailureType.UNKNOWN


def decide_execution_failure(
    *,
    action_id: str,
    idempotency_key: str,
    tool_name: str,
    error: Exception,
    attempt_number: int,
    max_attempts: int,
    prior_execution_completed: bool = False,
) -> ExecutionFailureDecision:
    failure_type = classify_execution_failure(error)

    disposition = evaluate_failure_policy(
        ExecutionFailureContext(
            action_id=action_id,
            idempotency_key=idempotency_key,
            failure_type=failure_type,
            attempt_number=attempt_number,
            max_attempts=max_attempts,
            prior_execution_completed=prior_execution_completed,
        )
    )

    if (
        disposition == FailureDisposition.RETRY
        and tool_name not in SAFE_AUTO_RETRY_TOOLS
    ):
        disposition = FailureDisposition.FAIL_CLOSED

    return ExecutionFailureDecision(
        failure_type=failure_type,
        disposition=disposition,
    )
