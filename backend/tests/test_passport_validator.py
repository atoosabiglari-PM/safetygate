from app.core.recertification.passport_validator import (
    PassportValidationStatus,
    validate_passport,
)


def test_active_matching_passport_is_valid() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
    )

    assert result.status == PassportValidationStatus.VALID


def test_configuration_change_requires_recertification() -> None:
    result = validate_passport(
        passport_status="ACTIVE",
        passport_configuration_hash="abc123",
        current_configuration_hash="different456",
    )

    assert result.status == PassportValidationStatus.RECERTIFICATION_REQUIRED


def test_inactive_passport_is_invalid() -> None:
    result = validate_passport(
        passport_status="REVOKED",
        passport_configuration_hash="abc123",
        current_configuration_hash="abc123",
    )

    assert result.status == PassportValidationStatus.INVALID
