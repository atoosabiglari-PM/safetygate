from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import ApprovalEvidenceRecord, RuntimeAuditEntry
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import HumanApprovalContext


def save_runtime_audit_entry(
    session: Session,
    record: RuntimeAuditRecord,
) -> RuntimeAuditEntry:
    entry = RuntimeAuditEntry(
        event_id=record.event_id,
        timestamp=record.timestamp,
        action_id=record.action_id,
        agent_id=record.agent_id,
        agent_version_id=record.agent_version_id,
        passport_id=record.passport_id,
        tool_name=record.tool_name,
        action_name=record.action_name,
        requested_permissions=record.requested_permissions,
        passport_status=record.passport_status,
        certified_configuration_hash=record.certified_configuration_hash,
        current_configuration_hash=record.current_configuration_hash,
        approval_id=record.approval_id,
        approver_identity=record.approver_identity,
        human_approved=record.human_approved,
        decision=record.decision,
        reasons=record.reasons,
        conditions=record.conditions,
        evidence=record.evidence,
        principal_identity=record.principal_identity,
        principal_roles=record.principal_roles,
        enforcement_reasons=record.enforcement_reasons,
        policy_rule_id=record.policy_rule_id,
        policy_authority=record.policy_authority,
        policy_source_name=record.policy_source_name,
        policy_source_version=record.policy_source_version,
        policy_source_reference=record.policy_source_reference,
        policy_considered_rules=record.policy_considered_rules,
        execution_outcome=record.execution_outcome,
    )

    session.add(entry)
    session.commit()
    session.refresh(entry)

    return entry


def save_approval_evidence(
    session: Session,
    approval: HumanApprovalContext,
) -> ApprovalEvidenceRecord:
    existing = session.scalar(
        select(ApprovalEvidenceRecord).where(
            ApprovalEvidenceRecord.approval_id == approval.approval_id
        )
    )

    if existing is not None:
        if (
            existing.action_id != approval.action_id
            or existing.approver_identity != approval.approver_identity
            or existing.approved != approval.approved
        ):
            raise ValueError(
                "Approval ID was reused with different approval evidence."
            )

        return existing

    record = ApprovalEvidenceRecord(
        approval_id=approval.approval_id,
        action_id=approval.action_id,
        approver_identity=approval.approver_identity,
        approved=approval.approved,
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record
