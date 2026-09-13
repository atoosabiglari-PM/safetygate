from app.core.authorization.tool_gateway import (
    execute_governed_tool,
    reset_execution_records,
)
from app.schemas.tool_execution import (
    ToolExecutionRequest,
    ToolExecutionStatus,
)


def setup_function() -> None:
    reset_execution_records()


def test_valid_tool_execution_succeeds() -> None:
    request = ToolExecutionRequest(
        action_id="action-001",
        idempotency_key="idem-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-123"},
    )

    result = execute_governed_tool(request)

    assert result.status == ToolExecutionStatus.EXECUTED
    assert result.execution_attempted is True
    assert result.output["simulated"] is True


def test_invalid_arguments_fail_before_execution() -> None:
    request = ToolExecutionRequest(
        action_id="action-002",
        idempotency_key="idem-002",
        tool_name="read_documents",
        arguments={},
    )

    result = execute_governed_tool(request)

    assert result.status == ToolExecutionStatus.FAILED_CLOSED
    assert result.execution_attempted is False
    assert any(
        "schema validation" in reason.lower()
        for reason in result.reasons
    )


def test_duplicate_execution_is_suppressed() -> None:
    request = ToolExecutionRequest(
        action_id="action-003",
        idempotency_key="idem-003",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "SafetyGate test",
        },
    )

    first = execute_governed_tool(request)
    second = execute_governed_tool(request)

    assert first.status == ToolExecutionStatus.EXECUTED
    assert second.status == ToolExecutionStatus.DUPLICATE_SUPPRESSED
    assert second.execution_attempted is False


def test_idempotency_key_reuse_with_different_payload_fails_closed() -> None:
    first_request = ToolExecutionRequest(
        action_id="action-004",
        idempotency_key="idem-004",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "Original message",
        },
    )

    second_request = ToolExecutionRequest(
        action_id="action-004",
        idempotency_key="idem-004",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "Different message",
        },
    )

    first = execute_governed_tool(first_request)
    second = execute_governed_tool(second_request)

    assert first.status == ToolExecutionStatus.EXECUTED
    assert second.status == ToolExecutionStatus.FAILED_CLOSED
    assert second.execution_attempted is False
    assert any(
        "different action payload" in reason.lower()
        for reason in second.reasons
    )
