from datetime import UTC, datetime

import pytest
from app.core.audit.persistence import (
    save_approval_evidence,
    save_runtime_audit_entry,
)
from app.db.base import Base
from app.db.session import create_database_engine, create_session_factory
from app.models import audit  # noqa: F401
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import HumanApprovalContext


def test_runtime_audit_entry_is_persisted(tmp_path) -> None:
    database_path = tmp_path / "audit.db"
    engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    record = RuntimeAuditRecord(
        event_id="event-001",
        timestamp=datetime.now(UTC),
        action_id="action-001",
        agent_id="agent-001",
        agent_version_id="version-001",
        passport_id="passport-001",
        tool_name="read_documents",
        action_name="read_document",
        requested_permissions=["documents:read"],
        passport_status="ACTIVE",
        certified_configuration_hash="abc123",
        current_configuration_hash="abc123",
        approval_id=None,
        approver_identity=None,
        human_approved=None,
        decision="ALLOW",
        reasons=[],
        conditions=[],
        evidence={"source": "audit-test"},
        principal_identity="reader@example.com",
        principal_roles=["READER"],
        enforcement_reasons=[],
        execution_outcome="EXECUTED",
    )

    with session_factory() as session:
        saved = save_runtime_audit_entry(session, record)

        assert saved.event_id == "event-001"
        assert saved.action_id == "action-001"
        assert saved.decision == "ALLOW"
        assert saved.execution_outcome == "EXECUTED"
        assert saved.evidence["source"] == "audit-test"

    engine.dispose()


def test_approval_evidence_is_idempotent_and_tamper_detecting(tmp_path) -> None:
    database_path = tmp_path / "approval.db"
    engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    approval = HumanApprovalContext(
        approval_id="approval-001",
        action_id="action-001",
        approver_identity="approver@example.com",
        approved=True,
    )

    with session_factory() as session:
        first = save_approval_evidence(session, approval)
        second = save_approval_evidence(session, approval)

        assert first.id == second.id

        tampered = HumanApprovalContext(
            approval_id="approval-001",
            action_id="action-001",
            approver_identity="attacker@example.com",
            approved=True,
        )

        with pytest.raises(
            ValueError,
            match="Approval ID was reused",
        ):
            save_approval_evidence(session, tampered)

    engine.dispose()
