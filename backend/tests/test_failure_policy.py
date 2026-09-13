from app.core.authorization.failure_policy import evaluate_failure_policy
from app.schemas.failure import (
    ExecutionFailureContext,
    FailureDisposition,
    FailureType,
)


def make_context(**overrides) -> ExecutionFailureContext:
    data = {
        "action_id": "action-001",
        "idempotency_key": "idem-001",
        "failure_type": FailureType.TIMEOUT,
        "attempt_number": 1,
        "max_attempts": 3,
        "prior_execution_completed": False,
    }

    data.update(overrides)
    return ExecutionFailureContext(**data)


def test_timeout_retries_when_attempts_remain() -> None:
    result = evaluate_failure_policy(
        make_context(
            failure_type=FailureType.TIMEOUT,
            attempt_number=1,
            max_attempts=3,
        )
    )

    assert result == FailureDisposition.RETRY


def test_transient_failure_retries_when_attempts_remain() -> None:
    result = evaluate_failure_policy(
        make_context(
            failure_type=FailureType.TRANSIENT,
            attempt_number=2,
            max_attempts=3,
        )
    )

    assert result == FailureDisposition.RETRY


def test_retry_exhaustion_fails_closed() -> None:
    result = evaluate_failure_policy(
        make_context(
            failure_type=FailureType.TIMEOUT,
            attempt_number=3,
            max_attempts=3,
        )
    )

    assert result == FailureDisposition.FAIL_CLOSED


def test_completed_duplicate_is_suppressed() -> None:
    result = evaluate_failure_policy(
        make_context(
            prior_execution_completed=True,
        )
    )

    assert result == FailureDisposition.DUPLICATE_SUPPRESSED


def test_partial_failure_requires_human_review() -> None:
    result = evaluate_failure_policy(
        make_context(
            failure_type=FailureType.PARTIAL_FAILURE,
        )
    )

    assert result == FailureDisposition.HUMAN_REVIEW_REQUIRED


def test_unknown_failure_fails_closed() -> None:
    result = evaluate_failure_policy(
        make_context(
            failure_type=FailureType.UNKNOWN,
        )
    )

    assert result == FailureDisposition.FAIL_CLOSED
