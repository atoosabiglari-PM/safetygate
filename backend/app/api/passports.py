import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.certification import SafetyPassport
from app.models.governance import Agent, AgentVersion
from app.schemas.api import PassportIssueCreate, PassportRead
from app.services.passport_issuance import issue_signed_safety_passport

router = APIRouter(
    prefix="/api/v1/organizations/{organization_id}/agents/{agent_id}",
    tags=["Safety Passports"],
)


@router.post(
    "/passport",
    response_model=PassportRead,
    status_code=status.HTTP_201_CREATED,
)
def issue_passport(
    organization_id: UUID,
    agent_id: UUID,
    payload: PassportIssueCreate,
    session: Session = Depends(get_db),
) -> PassportRead:
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

    if version.certification_status != "ADMISSION_PASSED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent must pass admission before Safety Passport issuance.",
        )

    existing = session.scalar(
        select(SafetyPassport).where(
            SafetyPassport.agent_version_id == version.id,
            SafetyPassport.status == "ACTIVE",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active Safety Passport already exists for this version.",
        )

    key_version_name = os.getenv("SAFETYGATE_KMS_KEY_VERSION")
    if not key_version_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Safety Passport signing key is not configured.",
        )

    passport = issue_signed_safety_passport(
        session,
        organization_id=organization_id,
        agent_version_id=version.id,
        configuration_hash=version.configuration_hash,
        policy_version=payload.policy_version,
        risk_class=payload.risk_class,
        allowed_tools=payload.allowed_tools,
        conditional_tools=payload.conditional_tools,
        prohibited_tools=payload.prohibited_tools,
        human_approvers=payload.human_approvers,
        certification_reason=payload.certification_reason,
        key_version_name=key_version_name,
    )

    version.certification_status = "CERTIFIED"
    agent.status = "ACTIVE"
    session.commit()
    session.refresh(passport)

    return PassportRead(
        passport_id=passport.id,
        organization_id=organization_id,
        agent_id=agent.id,
        agent_version_id=version.id,
        configuration_hash=passport.configuration_hash,
        policy_version=passport.policy_version,
        risk_class=passport.risk_class,
        status=passport.status,
        allowed_tools=passport.allowed_tools,
        conditional_tools=passport.conditional_tools,
        prohibited_tools=passport.prohibited_tools,
        human_approvers=passport.human_approvers,
        signature_key_id=passport.signature_key_id or "",
        issued_at=passport.issued_at,
    )
