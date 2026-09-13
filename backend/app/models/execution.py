from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionRecord(Base):
    __tablename__ = "execution_records"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    action_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    request_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    result_payload: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
    )
