from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.admission.engine import evaluate_admission
from app.core.certification.config_hash import calculate_configuration_hash
from app.models.governance import Agent, AgentVersion, Organization
from app.schemas.admission import AdmissionDecision, AgentAdmissionRequest
from app.schemas.api import (
    AdmissionEvaluationCreate,
    AdmissionEvaluationRead,
    AgentRegistrationCreate,
    AgentRegistrationRead,
)

router = APIRouter(
    prefix="/api/v1/organizations/{organization_id}/agents",
    tags=["Agents"],
)


@router.post(
    "",
    response_model=AgentRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
def register_agent(
    organization_id: UUID,
    payload: AgentRegistrationCreate,
    session: Session = Depends(get_db),
) -> AgentRegistrationRead:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    existing = session.scalar(
        select(Agent).where(
            Agent.organization_id == organization_id,
            Agent.name == payload.name,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent name already exists in this organization.",
        )

    configuration = {
        "model_provider": payload.model_provider,
        "model_name": payload.model_name,
        "system_prompt_hash": payload.system_prompt_hash,
        "tools": payload.tools,
        "permissions": payload.permissions,
        "memory_config": payload.memory_config,
        "jurisdictions": payload.jurisdictions,
        "autonomy_level": payload.autonomy_level,
    }
    configuration_hash = calculate_configuration_hash(configuration)

    agent = Agent(
        organization_id=organization_id,
        name=payload.name,
        owner_identity=payload.owner_identity,
        purpose=payload.purpose,
        status="DRAFT",
    )
    session.add(agent)
    session.flush()

    version = AgentVersion(
        organization_id=organization_id,
        agent_id=agent.id,
        version_number=1,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        system_prompt_hash=payload.system_prompt_hash,
        tools=payload.tools,
        permissions=payload.permissions,
        memory_config=payload.memory_config,
        jurisdictions=payload.jurisdictions,
        autonomy_level=payload.autonomy_level,
        configuration_hash=configuration_hash,
        certification_status="UNCERTIFIED",
    )
    session.add(version)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent registration conflict.",
        ) from exc

    session.refresh(agent)
    session.refresh(version)

    return AgentRegistrationRead(
        agent_id=agent.id,
        agent_version_id=version.id,
        organization_id=organization_id,
        name=agent.name,
        status=agent.status,
        version_number=version.version_number,
        configuration_hash=version.configuration_hash,
        certification_status=version.certification_status,
    )



@router.post(
    "/{agent_id}/admission",
    response_model=AdmissionEvaluationRead,
)
def evaluate_agent_admission(
    organization_id: UUID,
    agent_id: UUID,
    payload: AdmissionEvaluationCreate,
    session: Session = Depends(get_db),
) -> AdmissionEvaluationRead:
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

    result = evaluate_admission(
        AgentAdmissionRequest(
            agent_name=agent.name,
            owner_identity=agent.owner_identity,
            purpose=agent.purpose,
            model_provider=version.model_provider,
            model_name=version.model_name,
            tools=version.tools,
            permissions=version.permissions,
            jurisdictions=version.jurisdictions,
            autonomy_level=version.autonomy_level,
            human_approval_actions=payload.human_approval_actions,
            prohibited_actions=payload.prohibited_actions,
        )
    )

    if result.decision == AdmissionDecision.PASS:
        agent.status = "ADMITTED"
        version.certification_status = "ADMISSION_PASSED"
    else:
        agent.status = "ADMISSION_FAILED"
        version.certification_status = "UNCERTIFIED"

    session.commit()

    return AdmissionEvaluationRead(
        organization_id=organization_id,
        agent_id=agent.id,
        agent_version_id=version.id,
        decision=result.decision.value,
        reasons=result.reasons,
        agent_status=agent.status,
        certification_status=version.certification_status,
    )
