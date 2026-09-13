from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.execution import ExecutionRecord
from app.schemas.tool_execution import (
    ExecutionRecordStatus,
    ToolExecutionResult,
    ToolExecutionStatus,
)


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
        status=ExecutionRecordStatus.PENDING.value,
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


def mark_stale_pending_uncertain(
    session: Session,
    *,
    record: ExecutionRecord,
    stale_after: timedelta,
    now: datetime | None = None,
) -> bool:
    if record.status != ExecutionRecordStatus.PENDING.value:
        return False

    current_time = now or datetime.now(UTC)
    updated_at = record.updated_at

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    if current_time - updated_at < stale_after:
        return False

    result = ToolExecutionResult(
        status=ToolExecutionStatus.UNCERTAIN,
        tool_name=record.tool_name,
        reasons=[
            (
                "Durable execution claim remained PENDING beyond the "
                "permitted recovery window; external execution outcome "
                "cannot be proven."
            )
        ],
        execution_attempted=True,
    )

    record.status = ExecutionRecordStatus.UNCERTAIN.value
    record.result_payload = result.model_dump(mode="json")
    record.updated_at = current_time

    session.commit()
    session.refresh(record)

    return True


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
