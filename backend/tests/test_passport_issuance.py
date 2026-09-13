from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.core.certification.kms_signer import KmsSignature
from app.core.certification.passport_payload import build_passport_payload
from app.services.passport_issuance import issue_signed_safety_passport
from sqlalchemy.orm import Session

KEY_VERSION_NAME = (
    "projects/safetygate-atoosa-2026/"
    "locations/global/"
    "keyRings/safetygate-dev/"
    "cryptoKeys/safety-passport-signing/"
    "cryptoKeyVersions/1"
)


def test_issue_signed_passport_signs_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    organization_id = uuid4()
    agent_version_id = uuid4()
    captured = {}

    def fake_sign(
        *,
        payload: bytes,
        key_version_name: str,
    ) -> KmsSignature:
        captured["payload"] = payload
        captured["key_version_name"] = key_version_name
        return KmsSignature(
            signature="signed-passport",
            signature_key_id=key_version_name,
        )

    monkeypatch.setattr(
        "app.services.passport_issuance.sign_passport_payload",
        fake_sign,
    )

    passport = issue_signed_safety_passport(
        session,
        organization_id=organization_id,
        agent_version_id=agent_version_id,
        configuration_hash="abc123",
        policy_version="policy-v1",
        risk_class="HIGH",
        allowed_tools=["read_documents"],
        conditional_tools=["send_message"],
        prohibited_tools=["delete_records"],
        human_approvers=["security@example.com"],
        certification_reason="Admission controls passed.",
        key_version_name=KEY_VERSION_NAME,
    )

    expected_payload = build_passport_payload(
        passport_id=str(passport.id),
        organization_id=str(organization_id),
        agent_version_id=str(agent_version_id),
        configuration_hash="abc123",
        policy_version="policy-v1",
        risk_class="HIGH",
        allowed_tools=["read_documents"],
        conditional_tools=["send_message"],
        prohibited_tools=["delete_records"],
        human_approvers=["security@example.com"],
        issued_at=passport.issued_at,
    )

    assert captured["payload"] == expected_payload
    assert captured["key_version_name"] == KEY_VERSION_NAME

    assert passport.signature == "signed-passport"
    assert passport.signature_key_id == KEY_VERSION_NAME
    assert passport.status == "ACTIVE"

    session.add.assert_called_once_with(passport)
    session.flush.assert_called_once_with()


def test_signing_failure_does_not_persist_unsigned_passport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)

    def fail_sign(**kwargs):
        raise RuntimeError("KMS signing unavailable.")

    monkeypatch.setattr(
        "app.services.passport_issuance.sign_passport_payload",
        fail_sign,
    )

    with pytest.raises(RuntimeError, match="KMS signing unavailable"):
        issue_signed_safety_passport(
            session,
            organization_id=uuid4(),
            agent_version_id=uuid4(),
            configuration_hash="abc123",
            policy_version="policy-v1",
            risk_class="HIGH",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=["delete_records"],
            human_approvers=[],
            certification_reason="Admission controls passed.",
            key_version_name=KEY_VERSION_NAME,
        )

    session.add.assert_not_called()
    session.flush.assert_not_called()
