from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.audit.persistence import save_approval_evidence, save_runtime_audit_entry
from app.models.certification import SafetyPassport
from app.models.governance import Agent, AgentVersion
from app.schemas.api import RuntimeAuthorizationCreate, RuntimeAuthorizationRead
from app.schemas.runtime import (
    ActionProposal,
    HumanApprovalContext,
    PassportContext,
    RuntimeAuthorizationRequest,
)
from app.services.runtime_authorization import authorize_runtime_action

router = APIRouter(
    prefix="/api/v1/organizations/{organization_id}/agents/{agent_id}",
    tags=["Runtime Authorization"],
)


@router.post(
    "/authorize",
    response_model=RuntimeAuthorizationRead,
)
def authorize_action(
    organization_id: UUID,
    agent_id: UUID,
    payload: RuntimeAuthorizationCreate,
    session: Session = Depends(get_db),
) -> RuntimeAuthorizationRead:
    agent = session.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == organization_id,
        )
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    if agent.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent is not active.",
        )

    version = session.scalar(
        select(AgentVersion)
        .where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.organization_id == organization_id,
        )
        .order_by(AgentVersion.version_number.desc())
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent version not found.",
        )

    passport = session.scalar(
        select(SafetyPassport)
        .where(
            SafetyPassport.organization_id == organization_id,
            SafetyPassport.agent_version_id == version.id,
            SafetyPassport.status == "ACTIVE",
        )
        .order_by(SafetyPassport.issued_at.desc())
    )
    if passport is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active Safety Passport exists for this agent version.",
        )

    approval = None
    if payload.approval is not None:
        approval = HumanApprovalContext(
            approval_id=payload.approval.approval_id,
            action_id=payload.action_id,
            approver_identity=payload.approval.approver_identity,
            approved=payload.approval.approved,
        )

    request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id=payload.action_id,
            agent_id=str(agent.id),
            agent_version_id=str(version.id),
            passport_id=str(passport.id),
            tool_name=payload.tool_name,
            action_name=payload.action_name,
            requested_permissions=payload.requested_permissions,
            is_irreversible=payload.is_irreversible,
            risk_level=payload.risk_level,
            evidence=payload.evidence,
        ),
        passport=PassportContext(
            passport_id=str(passport.id),
            organization_id=str(organization_id),
            agent_version_id=str(version.id),
            status=passport.status,
            certified_configuration_hash=passport.configuration_hash,
            current_configuration_hash=version.configuration_hash,
            policy_version=passport.policy_version,
            risk_class=passport.risk_class,
            allowed_tools=passport.allowed_tools,
            conditional_tools=passport.conditional_tools,
            prohibited_tools=passport.prohibited_tools,
            human_approvers=passport.human_approvers,
            issued_at=passport.issued_at.isoformat(),
            signature_key_id=passport.signature_key_id,
            signature=passport.signature,
        ),
        approval=approval,
    )

    outcome = authorize_runtime_action(request)

    if approval is not None:
        try:
            save_approval_evidence(session, approval)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    save_runtime_audit_entry(session, outcome.audit)

    return RuntimeAuthorizationRead(
        action_id=payload.action_id,
        passport_id=passport.id,
        decision=outcome.decision.decision.value,
        reasons=outcome.decision.reasons,
        conditions=outcome.decision.conditions,
        audit_event_id=outcome.audit.event_id,
    )
