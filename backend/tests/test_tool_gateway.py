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


def test_safe_read_tool_uses_authorized_fallback() -> None:
    def failing_executor(tool_name, arguments):
        raise TimeoutError("primary unavailable")

    def fallback_executor(tool_name, arguments):
        return {
            "tool": tool_name,
            "document_id": arguments["document_id"],
            "source": "fallback",
        }

    request = ToolExecutionRequest(
        action_id="action-fallback-001",
        idempotency_key="idem-fallback-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-123"},
    )

    result = execute_governed_tool(
        request,
        executor=failing_executor,
        fallback_executor=fallback_executor,
    )

    assert result.status == ToolExecutionStatus.FALLBACK_EXECUTED
    assert result.fallback_used is True
    assert result.output["source"] == "fallback"


def test_consequential_tool_does_not_use_automatic_fallback() -> None:
    def failing_executor(tool_name, arguments):
        raise TimeoutError("primary unavailable")

    def fallback_executor(tool_name, arguments):
        return {"unexpected": True}

    request = ToolExecutionRequest(
        action_id="action-fallback-002",
        idempotency_key="idem-fallback-002",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "Do not duplicate this action",
        },
    )

    result = execute_governed_tool(
        request,
        executor=failing_executor,
        fallback_executor=fallback_executor,
    )

    assert result.status == ToolExecutionStatus.FAILED_CLOSED
    assert result.fallback_used is False


def test_failed_safe_fallback_fails_closed() -> None:
    def failing_executor(tool_name, arguments):
        raise TimeoutError("primary unavailable")

    def failing_fallback(tool_name, arguments):
        raise RuntimeError("fallback unavailable")

    request = ToolExecutionRequest(
        action_id="action-fallback-003",
        idempotency_key="idem-fallback-003",
        tool_name="read_documents",
        arguments={"document_id": "doc-456"},
    )

    result = execute_governed_tool(
        request,
        executor=failing_executor,
        fallback_executor=failing_fallback,
    )

    assert result.status == ToolExecutionStatus.FAILED_CLOSED
    assert result.fallback_used is True


from app.core.authorization.execution_failure_handler import (
    PartialToolFailure,
)


def test_safe_read_retries_after_timeout_and_then_succeeds() -> None:
    attempts = {"count": 0}

    def flaky_executor(tool_name, arguments):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise TimeoutError("temporary timeout")

        return {
            "tool": tool_name,
            "document_id": arguments["document_id"],
            "attempt": attempts["count"],
        }

    request = ToolExecutionRequest(
        action_id="action-retry-001",
        idempotency_key="idem-retry-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-retry-001"},
    )

    result = execute_governed_tool(
        request,
        executor=flaky_executor,
        max_attempts=3,
    )

    assert result.status == ToolExecutionStatus.EXECUTED
    assert result.execution_attempted is True
    assert attempts["count"] == 2
    assert result.output["attempt"] == 2


def test_partial_failure_requires_human_review_without_retry() -> None:
    attempts = {"count": 0}

    def partial_executor(tool_name, arguments):
        attempts["count"] += 1
        raise PartialToolFailure("remote operation partially completed")

    request = ToolExecutionRequest(
        action_id="action-partial-001",
        idempotency_key="idem-partial-001",
        tool_name="read_documents",
        arguments={"document_id": "doc-partial-001"},
    )

    result = execute_governed_tool(
        request,
        executor=partial_executor,
        max_attempts=3,
    )

    assert result.status == ToolExecutionStatus.HUMAN_REVIEW_REQUIRED
    assert result.execution_attempted is True
    assert attempts["count"] == 1


def test_consequential_tool_timeout_is_not_automatically_retried() -> None:
    attempts = {"count": 0}

    def timeout_executor(tool_name, arguments):
        attempts["count"] += 1
        raise TimeoutError("delivery result unknown")

    request = ToolExecutionRequest(
        action_id="action-no-retry-001",
        idempotency_key="idem-no-retry-001",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "Do not send this twice.",
        },
    )

    result = execute_governed_tool(
        request,
        executor=timeout_executor,
        max_attempts=3,
    )

    assert result.status == ToolExecutionStatus.FAILED_CLOSED
    assert result.execution_attempted is True
    assert attempts["count"] == 1
