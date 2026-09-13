from app.schemas.failure import (
    ExecutionFailureContext,
    FailureDisposition,
    FailureType,
)


def evaluate_failure_policy(
    context: ExecutionFailureContext,
) -> FailureDisposition:
    if context.prior_execution_completed:
        return FailureDisposition.DUPLICATE_SUPPRESSED

    if context.failure_type in {
        FailureType.TIMEOUT,
        FailureType.TRANSIENT,
    }:
        if context.attempt_number < context.max_attempts:
            return FailureDisposition.RETRY

        return FailureDisposition.FAIL_CLOSED

    if context.failure_type == FailureType.PARTIAL_FAILURE:
        return FailureDisposition.HUMAN_REVIEW_REQUIRED

    return FailureDisposition.FAIL_CLOSED
