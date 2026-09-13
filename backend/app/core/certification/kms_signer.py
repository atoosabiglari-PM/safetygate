import base64
import hashlib
from dataclasses import dataclass

from google.cloud import kms


@dataclass(frozen=True)
class KmsSignature:
    signature: str
    signature_key_id: str


def sign_passport_payload(
    *,
    payload: bytes,
    key_version_name: str,
    client: kms.KeyManagementServiceClient | None = None,
) -> KmsSignature:
    if not payload:
        raise ValueError("Passport payload cannot be empty.")

    if not key_version_name.strip():
        raise ValueError("KMS key version name is required.")

    digest = hashlib.sha256(payload).digest()

    kms_client = client or kms.KeyManagementServiceClient()

    response = kms_client.asymmetric_sign(
        request={
            "name": key_version_name,
            "digest": {"sha256": digest},
        }
    )

    return KmsSignature(
        signature=base64.b64encode(response.signature).decode("ascii"),
        signature_key_id=key_version_name,
    )
