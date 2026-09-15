import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.audit.persistence import save_approval_evidence
from app.models.audit import ApprovalEvidenceRecord, RuntimeAuditEntry
from app.models.certification import SafetyPassport
from app.models.governance import Agent, Organization
from app.schemas.runtime import HumanApprovalContext

router = APIRouter(
    prefix="/api/v1/organizations/{organization_id}/operator",
    tags=["Operator Console"],
)


class ReviewDecisionCreate(BaseModel):
    approver_identity: str = Field(min_length=1)
    approved: bool


def _organization_agent_ids(
    session: Session,
    organization_id: UUID,
) -> list[str]:
    organization = session.get(Organization, organization_id)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    ids = session.scalars(
        select(Agent.id).where(
            Agent.organization_id == organization_id
        )
    ).all()

    return [str(agent_id) for agent_id in ids]


def _serialize_audit(entry: RuntimeAuditEntry) -> dict:
    return {
        "event_id": entry.event_id,
        "timestamp": entry.timestamp,
        "action_id": entry.action_id,
        "agent_id": entry.agent_id,
        "agent_version_id": entry.agent_version_id,
        "passport_id": entry.passport_id,
        "tool_name": entry.tool_name,
        "action_name": entry.action_name,
        "requested_permissions": entry.requested_permissions,
        "decision": entry.decision,
        "reasons": entry.reasons,
        "conditions": entry.conditions,
        "approval_id": entry.approval_id,
        "approver_identity": entry.approver_identity,
        "human_approved": entry.human_approved,
        "principal_identity": entry.principal_identity,
        "principal_roles": entry.principal_roles,
        "policy_rule_id": entry.policy_rule_id,
        "policy_authority": entry.policy_authority,
        "policy_source_name": entry.policy_source_name,
        "policy_source_version": entry.policy_source_version,
        "policy_source_reference": entry.policy_source_reference,
        "execution_outcome": entry.execution_outcome,
        "evidence": entry.evidence,
    }


def _reviewed_action_ids(
    session: Session,
    action_ids: list[str],
) -> set[str]:
    if not action_ids:
        return set()

    reviewed = session.scalars(
        select(ApprovalEvidenceRecord.action_id).where(
            ApprovalEvidenceRecord.action_id.in_(action_ids)
        )
    ).all()

    return set(reviewed)


@router.get("/audit")
def list_audit_entries(
    organization_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_db),
) -> list[dict]:
    agent_ids = _organization_agent_ids(
        session,
        organization_id,
    )

    if not agent_ids:
        return []

    entries = session.scalars(
        select(RuntimeAuditEntry)
        .where(RuntimeAuditEntry.agent_id.in_(agent_ids))
        .order_by(RuntimeAuditEntry.timestamp.desc())
        .limit(limit)
    ).all()

    return [_serialize_audit(entry) for entry in entries]


@router.get("/reviews")
def list_pending_reviews(
    organization_id: UUID,
    session: Session = Depends(get_db),
) -> list[dict]:
    agent_ids = _organization_agent_ids(
        session,
        organization_id,
    )

    if not agent_ids:
        return []

    entries = session.scalars(
        select(RuntimeAuditEntry)
        .where(RuntimeAuditEntry.agent_id.in_(agent_ids))
        .order_by(RuntimeAuditEntry.timestamp.desc())
    ).all()

    latest_by_action: dict[str, RuntimeAuditEntry] = {}

    for entry in entries:
        if entry.action_id not in latest_by_action:
            latest_by_action[entry.action_id] = entry

    reviewed_actions = _reviewed_action_ids(
        session,
        list(latest_by_action),
    )

    pending = [
        entry
        for entry in latest_by_action.values()
        if (
            entry.decision == "HUMAN_REVIEW_REQUIRED"
            and entry.action_id not in reviewed_actions
        )
    ]

    return [_serialize_audit(entry) for entry in pending]


@router.get("/summary")
def operator_summary(
    organization_id: UUID,
    session: Session = Depends(get_db),
) -> dict:
    agent_ids = _organization_agent_ids(
        session,
        organization_id,
    )

    agents = session.scalars(
        select(Agent).where(
            Agent.organization_id == organization_id
        )
    ).all()

    if agent_ids:
        audits = session.scalars(
            select(RuntimeAuditEntry)
            .where(RuntimeAuditEntry.agent_id.in_(agent_ids))
            .order_by(RuntimeAuditEntry.timestamp.desc())
        ).all()
    else:
        audits = []

    latest_by_action: dict[str, RuntimeAuditEntry] = {}

    for entry in audits:
        if entry.action_id not in latest_by_action:
            latest_by_action[entry.action_id] = entry

    reviewed_actions = _reviewed_action_ids(
        session,
        list(latest_by_action),
    )

    pending_reviews = sum(
        1
        for entry in latest_by_action.values()
        if (
            entry.decision == "HUMAN_REVIEW_REQUIRED"
            and entry.action_id not in reviewed_actions
        )
    )

    hard_denies = sum(
        1
        for entry in audits
        if entry.decision in {
            "DENY",
            "NON_OVERRIDABLE_DENY",
        }
    )

    return {
        "organization_id": organization_id,
        "agents_total": len(agents),
        "agents_active": sum(
            1 for agent in agents if agent.status == "ACTIVE"
        ),
        "runtime_events": len(audits),
        "pending_reviews": pending_reviews,
        "hard_denies": hard_denies,
    }


@router.post("/reviews/{action_id}/decision")
def decide_review(
    organization_id: UUID,
    action_id: str,
    payload: ReviewDecisionCreate,
    session: Session = Depends(get_db),
) -> dict:
    agent_ids = _organization_agent_ids(
        session,
        organization_id,
    )

    if not agent_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No agents exist for this organization.",
        )

    entry = session.scalar(
        select(RuntimeAuditEntry)
        .where(
            RuntimeAuditEntry.agent_id.in_(agent_ids),
            RuntimeAuditEntry.action_id == action_id,
        )
        .order_by(RuntimeAuditEntry.timestamp.desc())
    )

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review action not found.",
        )

    if entry.decision != "HUMAN_REVIEW_REQUIRED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Action is not awaiting human review.",
        )

    try:
        passport_id = UUID(entry.passport_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit entry contains an invalid passport reference.",
        ) from exc

    passport = session.scalar(
        select(SafetyPassport).where(
            SafetyPassport.id == passport_id,
            SafetyPassport.organization_id == organization_id,
            SafetyPassport.status == "ACTIVE",
        )
    )

    if passport is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active Safety Passport not found.",
        )

    if payload.approver_identity not in passport.human_approvers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer is not authorized by the Safety Passport.",
        )

    approval = HumanApprovalContext(
        approval_id=f"review-{uuid4()}",
        action_id=action_id,
        approver_identity=payload.approver_identity,
        approved=payload.approved,
    )

    save_approval_evidence(session, approval)

    return {
        "approval_id": approval.approval_id,
        "action_id": action_id,
        "approver_identity": approval.approver_identity,
        "approved": approval.approved,
        "status": (
            "APPROVED"
            if approval.approved
            else "REJECTED"
        ),
    }


@router.get("/policy")
def policy_visibility(
    organization_id: UUID,
    session: Session = Depends(get_db),
) -> dict:
    _organization_agent_ids(
        session,
        organization_id,
    )

    return {
        "enforcement_model": (
            "Python hard gates enforce identity, signed Safety Passport, "
            "configuration, tool and permission boundaries. OPA/Rego may "
            "make the result more restrictive, never less restrictive."
        ),
        "opa_configured": bool(
            os.getenv("SAFETYGATE_OPA_URL", "").strip()
        ),
        "opa_policy_path": (
            "/v1/data/safetygate/runtime/rule_decisions"
        ),
        "authority_hierarchy": [
            "Mandatory Law",
            "Fundamental Rights",
            "AI Governance Standards",
            "Security Standards",
            "Organization Policy",
            "Agent Identity & Permissions",
            "Human Authority",
            "Runtime Evidence",
        ],
        "fail_closed": True,
    }
