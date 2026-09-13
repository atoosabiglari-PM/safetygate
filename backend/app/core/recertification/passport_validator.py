from dataclasses import dataclass
from enum import Enum


class PassportValidationStatus(str, Enum):
    VALID = "VALID"
    RECERTIFICATION_REQUIRED = "RECERTIFICATION_REQUIRED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class PassportValidationResult:
    status: PassportValidationStatus
    reason: str


def validate_passport(
    *,
    passport_status: str,
    passport_configuration_hash: str,
    current_configuration_hash: str,
) -> PassportValidationResult:
    if passport_status != "ACTIVE":
        return PassportValidationResult(
            status=PassportValidationStatus.INVALID,
            reason=f"Passport status is {passport_status}, not ACTIVE.",
        )

    if passport_configuration_hash != current_configuration_hash:
        return PassportValidationResult(
            status=PassportValidationStatus.RECERTIFICATION_REQUIRED,
            reason="Agent configuration no longer matches the certified configuration.",
        )

    return PassportValidationResult(
        status=PassportValidationStatus.VALID,
        reason="Passport is active and matches the current agent configuration.",
    )
