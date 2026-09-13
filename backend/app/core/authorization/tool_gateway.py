import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.authorization.execution_failure_handler import (
    decide_execution_failure,
)
from app.core.authorization.execution_store import (
    claim_execution_record,
    complete_execution_record,
    mark_stale_pending_uncertain,
)
from app.schemas.failure import FailureDisposition, FailureType
from app.schemas.tool_execution import (
    ExecutionRecordStatus,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
)


class ReadDocumentsArguments(BaseModel):
    document_id: str = Field(min_length=1)


class SendMessageArguments(BaseModel):
    recipient: str = Field(min_length=1)
    message: str = Field(min_length=1)


class DeployServiceArguments(BaseModel):
    service_name: str = Field(min_length=1)
    version: str = Field(min_length=1)


TOOL_ARGUMENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "read_documents": ReadDocumentsArguments,
    "send_message": SendMessageArguments,
    "deploy_service": DeployServiceArguments,
}


SAFE_FALLBACK_TOOLS = {"read_documents"}

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

_EXECUTION_RECORDS: dict[str, tuple[str, ToolExecutionResult]] = {}


def _request_fingerprint(request: ToolExecutionRequest) -> str:
    canonical = json.dumps(
        {
            "action_id": request.action_id,
            "tool_name": request.tool_name,
            "arguments": request.arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _execute_simulated_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "arguments": arguments,
        "simulated": True,
    }


def _finalize_execution_result(
    *,
    request: ToolExecutionRequest,
    fingerprint: str,
    result: ToolExecutionResult,
    session: Session | None,
    execution_record: Any | None,
) -> ToolExecutionResult:
    if session is not None and execution_record is not None:
        complete_execution_record(
            session,
            record=execution_record,
            result=result,
        )
    else:
        _EXECUTION_RECORDS[request.idempotency_key] = (
            fingerprint,
            result,
        )

    return result


def execute_governed_tool(
    request: ToolExecutionRequest,
    *,
    executor: ToolExecutor | None = None,
    fallback_executor: ToolExecutor | None = None,
    max_attempts: int = 3,
    session: Session | None = None,
    pending_stale_after: timedelta = timedelta(minutes=5),
) -> ToolExecutionResult:
    schema = TOOL_ARGUMENT_SCHEMAS.get(request.tool_name)

    if schema is None:
        return ToolExecutionResult(
            status=ToolExecutionStatus.FAILED_CLOSED,
            tool_name=request.tool_name,
            reasons=[
                f"Tool '{request.tool_name}' has no registered execution schema."
            ],
            execution_attempted=False,
        )

    try:
        validated = schema.model_validate(request.arguments)
    except ValidationError as exc:
        return ToolExecutionResult(
            status=ToolExecutionStatus.FAILED_CLOSED,
            tool_name=request.tool_name,
            reasons=[
                "Tool arguments failed schema validation.",
                str(exc),
            ],
            execution_attempted=False,
        )

    fingerprint = _request_fingerprint(request)

    execution_record = None

    if session is not None:
        claimed, execution_record = claim_execution_record(
            session,
            idempotency_key=request.idempotency_key,
            action_id=request.action_id,
            tool_name=request.tool_name,
            request_fingerprint=fingerprint,
        )

        if not claimed:
            if execution_record.request_fingerprint != fingerprint:
                return ToolExecutionResult(
                    status=ToolExecutionStatus.FAILED_CLOSED,
                    tool_name=request.tool_name,
                    reasons=[
                        "Idempotency key was reused for a different action payload."
                    ],
                    execution_attempted=False,
                )

            if execution_record.status == ExecutionRecordStatus.PENDING.value:
                became_uncertain = mark_stale_pending_uncertain(
                    session,
                    record=execution_record,
                    stale_after=pending_stale_after,
                )

                if became_uncertain:
                    return ToolExecutionResult.model_validate(
                        execution_record.result_payload
                    )

            if execution_record.status == ExecutionRecordStatus.UNCERTAIN.value:
                return ToolExecutionResult.model_validate(
                    execution_record.result_payload
                )

            return ToolExecutionResult(
                status=ToolExecutionStatus.DUPLICATE_SUPPRESSED,
                tool_name=request.tool_name,
                reasons=[
                    "Duplicate execution suppressed by atomic durable idempotency control."
                ],
                execution_attempted=False,
            )

    existing = (
        _EXECUTION_RECORDS.get(request.idempotency_key)
        if session is None
        else None
    )

    if existing is not None:
        existing_fingerprint, _ = existing

        if existing_fingerprint != fingerprint:
            return ToolExecutionResult(
                status=ToolExecutionStatus.FAILED_CLOSED,
                tool_name=request.tool_name,
                reasons=[
                    "Idempotency key was reused for a different action payload."
                ],
                execution_attempted=False,
            )

        return ToolExecutionResult(
            status=ToolExecutionStatus.DUPLICATE_SUPPRESSED,
            tool_name=request.tool_name,
            reasons=[
                "Duplicate execution suppressed by idempotency control."
            ],
            execution_attempted=False,
        )

    primary_executor = executor or _execute_simulated_tool
    validated_arguments = validated.model_dump()

    for attempt_number in range(1, max_attempts + 1):
        try:
            output = primary_executor(
                request.tool_name,
                validated_arguments,
            )
        except Exception as primary_error:  # noqa: BLE001
            failure = decide_execution_failure(
                action_id=request.action_id,
                idempotency_key=request.idempotency_key,
                tool_name=request.tool_name,
                error=primary_error,
                attempt_number=attempt_number,
                max_attempts=max_attempts,
            )

            if failure.disposition == FailureDisposition.RETRY:
                continue

            if (
                failure.disposition
                == FailureDisposition.HUMAN_REVIEW_REQUIRED
            ):
                result = ToolExecutionResult(
                    status=ToolExecutionStatus.HUMAN_REVIEW_REQUIRED,
                    tool_name=request.tool_name,
                    reasons=[
                        "Partial execution failure requires human review."
                    ],
                    execution_attempted=True,
                )

                return _finalize_execution_result(
                    request=request,
                    fingerprint=fingerprint,
                    result=result,
                    session=session,
                    execution_record=execution_record,
                )

            if (
                failure.failure_type
                in {FailureType.TIMEOUT, FailureType.TRANSIENT}
                and request.tool_name in SAFE_FALLBACK_TOOLS
                and fallback_executor is not None
            ):
                try:
                    fallback_output = fallback_executor(
                        request.tool_name,
                        validated_arguments,
                    )
                except Exception as fallback_error:  # noqa: BLE001
                    fallback_failure = decide_execution_failure(
                        action_id=request.action_id,
                        idempotency_key=request.idempotency_key,
                        tool_name=request.tool_name,
                        error=fallback_error,
                        attempt_number=1,
                        max_attempts=1,
                    )

                    if (
                        fallback_failure.disposition
                        == FailureDisposition.HUMAN_REVIEW_REQUIRED
                    ):
                        result = ToolExecutionResult(
                            status=(
                                ToolExecutionStatus.HUMAN_REVIEW_REQUIRED
                            ),
                            tool_name=request.tool_name,
                            reasons=[
                                "Fallback partially failed and requires human review."
                            ],
                            execution_attempted=True,
                            fallback_used=True,
                        )

                        return _finalize_execution_result(
                            request=request,
                            fingerprint=fingerprint,
                            result=result,
                            session=session,
                            execution_record=execution_record,
                        )

                    result = ToolExecutionResult(
                        status=ToolExecutionStatus.FAILED_CLOSED,
                        tool_name=request.tool_name,
                        reasons=[
                            "Primary execution exhausted safe retries.",
                            "Authorized fallback also failed.",
                        ],
                        execution_attempted=True,
                        fallback_used=True,
                    )

                    return _finalize_execution_result(
                        request=request,
                        fingerprint=fingerprint,
                        result=result,
                        session=session,
                        execution_record=execution_record,
                    )

                result = ToolExecutionResult(
                    status=ToolExecutionStatus.FALLBACK_EXECUTED,
                    tool_name=request.tool_name,
                    output=fallback_output,
                    reasons=[
                        "Primary execution exhausted safe retries.",
                        "Authorized safe fallback completed.",
                    ],
                    execution_attempted=True,
                    fallback_used=True,
                )

                return _finalize_execution_result(
                    request=request,
                    fingerprint=fingerprint,
                    result=result,
                    session=session,
                    execution_record=execution_record,
                )

            result = ToolExecutionResult(
                status=ToolExecutionStatus.FAILED_CLOSED,
                tool_name=request.tool_name,
                reasons=[
                    (
                        "Execution failure was not eligible for "
                        "automatic retry or fallback."
                    )
                ],
                execution_attempted=True,
            )

            return _finalize_execution_result(
                request=request,
                fingerprint=fingerprint,
                result=result,
                session=session,
                execution_record=execution_record,
            )

        result = ToolExecutionResult(
            status=ToolExecutionStatus.EXECUTED,
            tool_name=request.tool_name,
            output=output,
            reasons=[
                (
                    "Tool arguments validated and execution completed "
                    f"on attempt {attempt_number}."
                )
            ],
            execution_attempted=True,
        )

        return _finalize_execution_result(
            request=request,
            fingerprint=fingerprint,
            result=result,
            session=session,
            execution_record=execution_record,
        )

    result = ToolExecutionResult(
        status=ToolExecutionStatus.FAILED_CLOSED,
        tool_name=request.tool_name,
        reasons=["Execution exhausted all permitted attempts."],
        execution_attempted=True,
    )

    return _finalize_execution_result(
        request=request,
        fingerprint=fingerprint,
        result=result,
        session=session,
        execution_record=execution_record,
    )


def reset_execution_records() -> None:
    _EXECUTION_RECORDS.clear()
