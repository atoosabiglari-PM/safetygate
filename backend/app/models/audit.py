from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RuntimeAuditEntry(Base):
    __tablename__ = "runtime_audit_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )

    event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    action_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_version_id: Mapped[str] = mapped_column(String(255), nullable=False)
    passport_id: Mapped[str] = mapped_column(String(255), nullable=False)

    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_permissions: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    passport_status: Mapped[str] = mapped_column(String(50), nullable=False)
    certified_configuration_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    current_configuration_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    approval_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    approver_identity: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    human_approved: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    conditions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    principal_identity: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    principal_roles: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    enforcement_reasons: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    policy_rule_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    policy_authority: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    policy_source_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    policy_source_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    policy_source_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    policy_considered_rules: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    execution_outcome: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
    )


class ApprovalEvidenceRecord(Base):
    __tablename__ = "approval_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4,
        primary_key=True,
    )

    approval_id: Mapped[str] = mapped_column(
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

    approver_identity: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
    )
