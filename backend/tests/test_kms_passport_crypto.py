import base64
import hashlib
from types import SimpleNamespace

from app.core.certification.kms_signer import sign_passport_payload
from app.core.certification.kms_verifier import verify_passport_signature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

KEY_VERSION_NAME = (
    "projects/safetygate-atoosa-2026/"
    "locations/global/"
    "keyRings/safetygate-dev/"
    "cryptoKeys/safety-passport-signing/"
    "cryptoKeyVersions/1"
)


class FakeKmsClient:
    def __init__(self) -> None:
        self.private_key = ec.generate_private_key(ec.SECP256R1())

    def asymmetric_sign(self, *, request):
        digest = request["digest"]["sha256"]

        signature = self.private_key.sign(
            digest,
            ec.ECDSA(utils.Prehashed(hashes.SHA256())),
        )

        return SimpleNamespace(signature=signature)

    def get_public_key(self, *, request):
        public_key = self.private_key.public_key()

        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        return SimpleNamespace(pem=pem)


def test_signer_returns_base64_signature_and_exact_key_version() -> None:
    payload = b'{"passport_id":"passport-001"}'
    client = FakeKmsClient()

    result = sign_passport_payload(
        payload=payload,
        key_version_name=KEY_VERSION_NAME,
        client=client,
    )

    assert result.signature_key_id == KEY_VERSION_NAME
    assert base64.b64decode(result.signature, validate=True)


def test_signer_sends_sha256_digest_to_kms() -> None:
    payload = b'{"passport_id":"passport-001"}'
    expected_digest = hashlib.sha256(payload).digest()

    class DigestCheckingClient(FakeKmsClient):
        def asymmetric_sign(self, *, request):
            assert request["name"] == KEY_VERSION_NAME
            assert request["digest"]["sha256"] == expected_digest
            return super().asymmetric_sign(request=request)

    sign_passport_payload(
        payload=payload,
        key_version_name=KEY_VERSION_NAME,
        client=DigestCheckingClient(),
    )


def test_verifier_accepts_valid_signature() -> None:
    payload = b'{"passport_id":"passport-001","risk_class":"HIGH"}'
    client = FakeKmsClient()

    signed = sign_passport_payload(
        payload=payload,
        key_version_name=KEY_VERSION_NAME,
        client=client,
    )

    assert verify_passport_signature(
        payload=payload,
        signature=signed.signature,
        key_version_name=signed.signature_key_id,
        client=client,
    )


def test_verifier_rejects_tampered_payload() -> None:
    payload = b'{"passport_id":"passport-001","risk_class":"HIGH"}'
    client = FakeKmsClient()

    signed = sign_passport_payload(
        payload=payload,
        key_version_name=KEY_VERSION_NAME,
        client=client,
    )

    tampered = payload.replace(
        b'"risk_class":"HIGH"',
        b'"risk_class":"LOW"',
    )

    assert not verify_passport_signature(
        payload=tampered,
        signature=signed.signature,
        key_version_name=signed.signature_key_id,
        client=client,
    )


def test_verifier_rejects_invalid_base64_signature() -> None:
    assert not verify_passport_signature(
        payload=b'{"passport_id":"passport-001"}',
        signature="not-valid-base64%%%",
        key_version_name=KEY_VERSION_NAME,
        client=FakeKmsClient(),
    )


def test_signer_rejects_empty_payload() -> None:
    try:
        sign_passport_payload(
            payload=b"",
            key_version_name=KEY_VERSION_NAME,
            client=FakeKmsClient(),
        )
    except ValueError as exc:
        assert "cannot be empty" in str(exc)
    else:
        raise AssertionError("Empty passport payload did not fail closed.")


def test_verifier_rejects_signature_from_wrong_key_version() -> None:
    payload = b'{"passport_id":"passport-001"}'
    signing_client = FakeKmsClient()
    wrong_key_client = FakeKmsClient()

    signed = sign_passport_payload(
        payload=payload,
        key_version_name=KEY_VERSION_NAME,
        client=signing_client,
    )

    wrong_key_version = (
        "projects/safetygate-atoosa-2026/"
        "locations/global/"
        "keyRings/safetygate-dev/"
        "cryptoKeys/safety-passport-signing/"
        "cryptoKeyVersions/999"
    )

    assert not verify_passport_signature(
        payload=payload,
        signature=signed.signature,
        key_version_name=wrong_key_version,
        client=wrong_key_client,
    )


def test_verifier_fails_closed_on_google_auth_error() -> None:
    from google.auth.exceptions import GoogleAuthError

    class AuthFailingClient:
        def get_public_key(self, *, request):
            raise GoogleAuthError("credentials unavailable")

    assert not verify_passport_signature(
        payload=b'{"passport_id":"passport-001"}',
        signature="dGVzdA==",
        key_version_name=KEY_VERSION_NAME,
        client=AuthFailingClient(),
    )



def test_passport_payload_survives_database_timestamp_roundtrip() -> None:
    from datetime import UTC, datetime

    from app.core.certification.passport_payload import build_passport_payload

    aware = datetime(
        2026, 9, 15, 17, 0, 0, 123456,
        tzinfo=UTC,
    )

    fields = {
        "passport_id": "passport-001",
        "organization_id": "org-001",
        "agent_version_id": "version-001",
        "configuration_hash": "a" * 64,
        "policy_version": "1.0",
        "risk_class": "HIGH",
        "allowed_tools": ["read_documents"],
        "conditional_tools": [],
        "prohibited_tools": [],
        "human_approvers": ["reviewer"],
    }

    signed_payload = build_passport_payload(
        **fields,
        issued_at=aware,
    )

    database_roundtrip_payload = build_passport_payload(
        **fields,
        issued_at=aware.replace(tzinfo=None).isoformat(),
    )

    assert signed_payload == database_roundtrip_payload
