from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.governance import Organization
from app.schemas.api import OrganizationCreate, OrganizationRead

router = APIRouter(prefix="/api/v1", tags=["SafetyGate API"])


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    session: Session = Depends(get_db),
) -> Organization:
    existing = session.scalar(
        select(Organization).where(Organization.name == payload.name)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization name already exists.",
        )

    organization = Organization(name=payload.name)
    session.add(organization)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization name already exists.",
        ) from exc

    session.refresh(organization)
    return organization
