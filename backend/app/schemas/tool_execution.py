from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    FALLBACK_EXECUTED = "FALLBACK_EXECUTED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    FAILED_CLOSED = "FAILED_CLOSED"


class ToolExecutionRequest(BaseModel):
    action_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    status: ToolExecutionStatus
    tool_name: str

    output: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)

    execution_attempted: bool = False
    fallback_used: bool = False
