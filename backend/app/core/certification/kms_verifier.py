import base64
import binascii
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from google.cloud import kms


def verify_passport_signature(
    *,
    payload: bytes,
    signature: str,
    key_version_name: str,
    client: kms.KeyManagementServiceClient | None = None,
) -> bool:
    if not payload or not signature.strip() or not key_version_name.strip():
        return False

    try:
        signature_bytes = base64.b64decode(
            signature,
            validate=True,
        )

        kms_client = client or kms.KeyManagementServiceClient()

        response = kms_client.get_public_key(
            request={"name": key_version_name}
        )

        public_key = serialization.load_pem_public_key(
            response.pem.encode("ascii")
        )

        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False

        if not isinstance(public_key.curve, ec.SECP256R1):
            return False

        digest = hashlib.sha256(payload).digest()

        public_key.verify(
            signature_bytes,
            digest,
            ec.ECDSA(utils.Prehashed(hashes.SHA256())),
        )

        return True

    except (
        InvalidSignature,
        ValueError,
        TypeError,
        binascii.Error,
        GoogleAPICallError,
        GoogleAuthError,
    ):
        return False
