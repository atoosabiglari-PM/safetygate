from datetime import datetime, timezone
from uuid import uuid4

from app.core.audit.redaction import redact_sensitive_data
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecisionResult,
)


def create_runtime_audit_record(
    request: RuntimeAuthorizationRequest,
    result: RuntimeDecisionResult,
    execution_outcome: str | None = None,
) -> RuntimeAuditRecord:
    proposal = request.proposal
    passport = request.passport
    approval = request.approval

    return RuntimeAuditRecord(
        event_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        action_id=proposal.action_id,
        agent_id=proposal.agent_id,
        agent_version_id=proposal.agent_version_id,
        passport_id=proposal.passport_id,
        tool_name=proposal.tool_name,
        action_name=proposal.action_name,
        requested_permissions=proposal.requested_permissions,
        passport_status=passport.status,
        certified_configuration_hash=passport.certified_configuration_hash,
        current_configuration_hash=passport.current_configuration_hash,
        approval_id=approval.approval_id if approval else None,
        approver_identity=approval.approver_identity if approval else None,
        human_approved=approval.approved if approval else None,
        decision=result.decision.value,
        reasons=result.reasons,
        conditions=result.conditions,
        evidence=redact_sensitive_data(proposal.evidence),
        execution_outcome=execution_outcome,
    )
