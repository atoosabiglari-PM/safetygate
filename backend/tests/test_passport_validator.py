from app.core.recertification.passport_validator import (
    PassportValidationStatus,
    validate_passport,
)

PAYLOAD = b'{"passport_id":"passport-001"}'
SIGNATURE = "valid-signature"
KEY_ID = (
    "projects/safetygate-atoosa-2026/"
    "locations/global/"
    "keyRings/safetygate-dev/"
    "cryptoKeys/safety-passport-signing/"
    "cryptoKeyVersions/1"
)


def valid_signature(**kwargs) -> bool:
    return True


def invalid_signature(**kwargs) -> bool:
    return False


def test_valid_signed_active_matching_passport_is_valid() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.VALID


def test_missing_signature_fails_closed() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
        signed_payload=PAYLOAD,
        signature=None,
        signature_key_id=KEY_ID,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID
    assert "signature" in result.reason.lower()


def test_missing_key_version_fails_closed() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=None,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID


def test_invalid_signature_fails_closed_before_status_check() -> None:
    result = validate_passport(
        passport_status="REVOKED",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=invalid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID
    assert "cryptographic signature" in result.reason.lower()


def test_configuration_change_requires_recertification() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="different456",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.RECERTIFICATION_REQUIRED


def test_inactive_passport_is_invalid() -> None:
    result = validate_passport(
        passport_status="REVOKED",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID


def test_invalid_signature_precedes_recertification_check() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="changed456",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=invalid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID
    assert "cryptographic signature" in result.reason.lower()


def test_inactive_status_precedes_configuration_recertification() -> None:
    result = validate_passport(
        passport_status="REVOKED",
        passport_configuration_hash="abc123",
        current_configuration_hash="changed456",
        signed_payload=PAYLOAD,
        signature=SIGNATURE,
        signature_key_id=KEY_ID,
        signature_verifier=valid_signature,
    )

    assert result.status == PassportValidationStatus.INVALID
    assert "status" in result.reason.lower()
