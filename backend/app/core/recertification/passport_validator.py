from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from app.core.certification.kms_verifier import verify_passport_signature


class PassportValidationStatus(str, Enum):
    VALID = "VALID"
    RECERTIFICATION_REQUIRED = "RECERTIFICATION_REQUIRED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class PassportValidationResult:
    status: PassportValidationStatus
    reason: str


SignatureVerifier = Callable[..., bool]


def validate_passport(
    *,
    passport_status: str,
    passport_configuration_hash: str,
    current_configuration_hash: str,
    signed_payload: bytes,
    signature: str | None,
    signature_key_id: str | None,
    signature_verifier: SignatureVerifier = verify_passport_signature,
) -> PassportValidationResult:
    if not signature or not signature_key_id:
        return PassportValidationResult(
            status=PassportValidationStatus.INVALID,
            reason="Safety Passport signature evidence is missing.",
        )

    signature_valid = signature_verifier(
        payload=signed_payload,
        signature=signature,
        key_version_name=signature_key_id,
    )

    if not signature_valid:
        return PassportValidationResult(
            status=PassportValidationStatus.INVALID,
            reason="Safety Passport cryptographic signature is invalid.",
        )

    if passport_status != "ACTIVE":
        return PassportValidationResult(
            status=PassportValidationStatus.INVALID,
            reason=f"Passport status is {passport_status}, not ACTIVE.",
        )

    if passport_configuration_hash != current_configuration_hash:
        return PassportValidationResult(
            status=PassportValidationStatus.RECERTIFICATION_REQUIRED,
            reason=(
                "Agent configuration no longer matches the "
                "certified configuration."
            ),
        )

    return PassportValidationResult(
        status=PassportValidationStatus.VALID,
        reason=(
            "Passport signature is valid, status is active, and "
            "configuration matches the certified configuration."
        ),
    )
