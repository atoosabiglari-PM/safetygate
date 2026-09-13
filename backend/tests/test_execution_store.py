from app.core.authorization.execution_store import (
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
