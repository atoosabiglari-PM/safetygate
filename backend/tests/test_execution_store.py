from app.core.authorization.execution_store import (
    claim_execution_record,
    get_execution_record,
    save_execution_record,
)
from app.db.base import Base
from app.db.session import (
    create_database_engine,
    create_session_factory,
)
from app.schemas.tool_execution import (
    ToolExecutionResult,
    ToolExecutionStatus,
)


def test_execution_record_survives_database_engine_restart(tmp_path) -> None:
    database_path = tmp_path / "execution.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    result = ToolExecutionResult(
        status=ToolExecutionStatus.EXECUTED,
        tool_name="read_documents",
        output={"document_id": "doc-001"},
        reasons=["Execution completed."],
        execution_attempted=True,
    )

    with session_factory() as session:
        save_execution_record(
            session,
            idempotency_key="idem-persistent-001",
            action_id="action-persistent-001",
            tool_name="read_documents",
            request_fingerprint="abc123",
            result=result,
        )

    engine.dispose()

    restarted_engine = create_database_engine(database_url)
    restarted_factory = create_session_factory(restarted_engine)

    with restarted_factory() as session:
        record = get_execution_record(
            session,
            idempotency_key="idem-persistent-001",
        )

        assert record is not None
        assert record.action_id == "action-persistent-001"
        assert record.tool_name == "read_documents"
        assert record.request_fingerprint == "abc123"
        assert record.status == "EXECUTED"
        assert record.result_payload["execution_attempted"] is True

    restarted_engine.dispose()


def test_gateway_suppresses_duplicate_after_restart(tmp_path) -> None:
    from app.core.authorization.tool_gateway import (
        execute_governed_tool,
        reset_execution_records,
    )
    from app.schemas.tool_execution import ToolExecutionRequest

    database_path = tmp_path / "gateway-restart.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    request = ToolExecutionRequest(
        action_id="action-restart-001",
        idempotency_key="idem-restart-001",
        tool_name="send_message",
        arguments={
            "recipient": "reviewer@example.com",
            "message": "Execute exactly once.",
        },
    )

    with session_factory() as session:
        first = execute_governed_tool(
            request,
            session=session,
        )

    assert first.status == ToolExecutionStatus.EXECUTED

    engine.dispose()

    # Simulate application/process restart: volatile memory is gone.
    reset_execution_records()

    restarted_engine = create_database_engine(database_url)
    restarted_factory = create_session_factory(restarted_engine)

    calls = {"count": 0}

    def executor(tool_name, arguments):
        calls["count"] += 1
        return {"unexpected": True}

    with restarted_factory() as session:
        second = execute_governed_tool(
            request,
            executor=executor,
            session=session,
        )

    assert second.status == ToolExecutionStatus.DUPLICATE_SUPPRESSED
    assert second.execution_attempted is False
    assert calls["count"] == 0

    restarted_engine.dispose()



def test_only_one_caller_can_claim_same_execution(tmp_path) -> None:
    database_path = tmp_path / "atomic-claim.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as first_session:
        first_claimed, first_record = claim_execution_record(
            first_session,
            idempotency_key="idem-atomic-001",
            action_id="action-atomic-001",
            tool_name="send_message",
            request_fingerprint="fingerprint-001",
        )

    with session_factory() as second_session:
        second_claimed, second_record = claim_execution_record(
            second_session,
            idempotency_key="idem-atomic-001",
            action_id="action-atomic-001",
            tool_name="send_message",
            request_fingerprint="fingerprint-001",
        )

    assert first_claimed is True
    assert first_record.status == "PENDING"

    assert second_claimed is False
    assert second_record.id == first_record.id
    assert second_record.status == "PENDING"

    engine.dispose()
