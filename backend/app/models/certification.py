from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SafetyPassport(Base):
    __tablename__ = "safety_passports"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    configuration_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    policy_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    risk_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    allowed_tools: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    conditional_tools: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    prohibited_tools: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    human_approvers: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False,
        index=True,
    )

    certification_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    signature_key_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    issued_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
