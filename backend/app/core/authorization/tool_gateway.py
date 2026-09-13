import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas.tool_execution import (
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


def execute_governed_tool(
    request: ToolExecutionRequest,
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

    existing = _EXECUTION_RECORDS.get(request.idempotency_key)

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

    output = _execute_simulated_tool(
        request.tool_name,
        validated.model_dump(),
    )

    result = ToolExecutionResult(
        status=ToolExecutionStatus.EXECUTED,
        tool_name=request.tool_name,
        output=output,
        reasons=[
            "Tool arguments validated and execution completed."
        ],
        execution_attempted=True,
    )

    _EXECUTION_RECORDS[request.idempotency_key] = (
        fingerprint,
        result,
    )

    return result


def reset_execution_records() -> None:
    _EXECUTION_RECORDS.clear()
