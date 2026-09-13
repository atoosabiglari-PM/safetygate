from enum import Enum

from pydantic import BaseModel, Field


class FailureType(str, Enum):
    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    UNKNOWN = "UNKNOWN"


class FailureDisposition(str, Enum):
    RETRY = "RETRY"
    FAIL_CLOSED = "FAIL_CLOSED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"


class ExecutionFailureContext(BaseModel):
    action_id: str
    idempotency_key: str = Field(min_length=1)

    failure_type: FailureType

    attempt_number: int = Field(ge=1)
    max_attempts: int = Field(ge=1, default=3)

    prior_execution_completed: bool = False
