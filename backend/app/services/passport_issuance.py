from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.certification.kms_signer import sign_passport_payload
from app.core.certification.passport_payload import build_passport_payload
from app.models.certification import SafetyPassport, utc_now


def issue_signed_safety_passport(
    session: Session,
    *,
    organization_id: UUID,
    agent_version_id: UUID,
    configuration_hash: str,
    policy_version: str,
    risk_class: str,
    allowed_tools: list[str],
    conditional_tools: list[str],
    prohibited_tools: list[str],
    human_approvers: list[str],
    certification_reason: str,
    key_version_name: str,
) -> SafetyPassport:
    passport = SafetyPassport(
        id=uuid4(),
        organization_id=organization_id,
        agent_version_id=agent_version_id,
        configuration_hash=configuration_hash,
        policy_version=policy_version,
        risk_class=risk_class,
        allowed_tools=list(allowed_tools),
        conditional_tools=list(conditional_tools),
        prohibited_tools=list(prohibited_tools),
        human_approvers=list(human_approvers),
        status="ACTIVE",
        certification_reason=certification_reason,
        issued_at=utc_now(),
    )

    payload = build_passport_payload(
        passport_id=str(passport.id),
        organization_id=str(passport.organization_id),
        agent_version_id=str(passport.agent_version_id),
        configuration_hash=passport.configuration_hash,
        policy_version=passport.policy_version,
        risk_class=passport.risk_class,
        allowed_tools=passport.allowed_tools,
        conditional_tools=passport.conditional_tools,
        prohibited_tools=passport.prohibited_tools,
        human_approvers=passport.human_approvers,
        issued_at=passport.issued_at,
    )

    signed = sign_passport_payload(
        payload=payload,
        key_version_name=key_version_name,
    )

    passport.signature_key_id = signed.signature_key_id
    passport.signature = signed.signature

    session.add(passport)
    session.flush()

    return passport
