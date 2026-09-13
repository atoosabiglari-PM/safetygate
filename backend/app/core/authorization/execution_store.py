from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.execution import ExecutionRecord
from app.schemas.tool_execution import ToolExecutionResult


def get_execution_record(
    session: Session,
    *,
    idempotency_key: str,
) -> ExecutionRecord | None:
    statement = select(ExecutionRecord).where(
        ExecutionRecord.idempotency_key == idempotency_key
    )

    return session.scalar(statement)


def save_execution_record(
    session: Session,
    *,
    idempotency_key: str,
    action_id: str,
    tool_name: str,
    request_fingerprint: str,
    result: ToolExecutionResult,
) -> ExecutionRecord:
    record = ExecutionRecord(
        idempotency_key=idempotency_key,
        action_id=action_id,
        tool_name=tool_name,
        request_fingerprint=request_fingerprint,
        status=result.status.value,
        result_payload=result.model_dump(mode="json"),
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record


def claim_execution_record(
    session: Session,
    *,
    idempotency_key: str,
    action_id: str,
    tool_name: str,
    request_fingerprint: str,
) -> tuple[bool, ExecutionRecord]:
    record = ExecutionRecord(
        idempotency_key=idempotency_key,
        action_id=action_id,
        tool_name=tool_name,
        request_fingerprint=request_fingerprint,
        status="PENDING",
        result_payload={},
    )

    session.add(record)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        existing = get_execution_record(
            session,
            idempotency_key=idempotency_key,
        )

        if existing is None:
            raise

        return False, existing

    session.refresh(record)

    return True, record


def complete_execution_record(
    session: Session,
    *,
    record: ExecutionRecord,
    result: ToolExecutionResult,
) -> ExecutionRecord:
    record.status = result.status.value
    record.result_payload = result.model_dump(mode="json")

    session.commit()
    session.refresh(record)

    return record
