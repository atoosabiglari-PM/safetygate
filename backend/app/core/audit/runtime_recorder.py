from datetime import UTC, datetime
from uuid import uuid4

from app.core.audit.redaction import redact_sensitive_data
from app.core.policy.resolver import PolicyResolution
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecisionResult,
)


def create_runtime_audit_record(
    request: RuntimeAuthorizationRequest,
    result: RuntimeDecisionResult,
    execution_outcome: str | None = None,
    policy_resolution: PolicyResolution | None = None,
) -> RuntimeAuditRecord:
    proposal = request.proposal
    passport = request.passport
    approval = request.approval

    policy_rule_id = None
    policy_authority = None
    policy_source_name = None
    policy_source_version = None
    policy_source_reference = None
    policy_considered_rules = []

    if policy_resolution is not None:
        winning = policy_resolution.winning_rule
        provenance = winning.provenance

        policy_rule_id = provenance.rule_id
        policy_authority = provenance.authority.name
        policy_source_name = provenance.source_name
        policy_source_version = provenance.source_version
        policy_source_reference = provenance.source_reference

        policy_considered_rules = [
            {
                "rule_id": rule.provenance.rule_id,
                "authority": rule.provenance.authority.name,
                "source_name": rule.provenance.source_name,
                "source_version": rule.provenance.source_version,
                "source_reference": rule.provenance.source_reference,
                "decision": rule.decision.value,
                "reason": rule.reason,
            }
            for rule in policy_resolution.considered_rules
        ]

    return RuntimeAuditRecord(
        event_id=str(uuid4()),
        timestamp=datetime.now(UTC),
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
        policy_rule_id=policy_rule_id,
        policy_authority=policy_authority,
        policy_source_name=policy_source_name,
        policy_source_version=policy_source_version,
        policy_source_reference=policy_source_reference,
        policy_considered_rules=policy_considered_rules,
        execution_outcome=execution_outcome,
    )
