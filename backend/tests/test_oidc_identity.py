from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.identity.oidc import (
    OIDCVerificationError,
    verify_oidc_token,
)
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://identity.example.com"
AUDIENCE = "safetygate"


def make_private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def make_claims(
    *,
    audience: str = AUDIENCE,
    expires_in: timedelta = timedelta(minutes=5),
) -> dict:
    now = datetime.now(UTC)

    return {
        "iss": ISSUER,
        "sub": "user-123",
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "email": "operator@example.com",
        "email_verified": True,
    }


def test_valid_signed_oidc_token_is_verified() -> None:
    private_key = make_private_key()
    public_key = private_key.public_key()

    token = jwt.encode(
        make_claims(),
        private_key,
        algorithm="RS256",
    )

    identity = verify_oidc_token(
        token=token,
        verification_key=public_key,
        issuer=ISSUER,
        audience=AUDIENCE,
    )

    assert identity.subject == "user-123"
    assert identity.email == "operator@example.com"
    assert identity.email_verified is True
    assert identity.issuer == ISSUER


def test_token_signed_by_untrusted_key_is_rejected() -> None:
    trusted_private_key = make_private_key()
    attacker_private_key = make_private_key()

    token = jwt.encode(
        make_claims(),
        attacker_private_key,
        algorithm="RS256",
    )

    with pytest.raises(
        OIDCVerificationError,
        match="OIDC token verification failed",
    ):
        verify_oidc_token(
            token=token,
            verification_key=trusted_private_key.public_key(),
            issuer=ISSUER,
            audience=AUDIENCE,
        )


def test_token_for_wrong_audience_is_rejected() -> None:
    private_key = make_private_key()

    token = jwt.encode(
        make_claims(audience="some-other-application"),
        private_key,
        algorithm="RS256",
    )

    with pytest.raises(
        OIDCVerificationError,
        match="OIDC token verification failed",
    ):
        verify_oidc_token(
            token=token,
            verification_key=private_key.public_key(),
            issuer=ISSUER,
            audience=AUDIENCE,
        )


def test_expired_token_is_rejected() -> None:
    private_key = make_private_key()

    token = jwt.encode(
        make_claims(expires_in=timedelta(minutes=-5)),
        private_key,
        algorithm="RS256",
    )

    with pytest.raises(
        OIDCVerificationError,
        match="OIDC token verification failed",
    ):
        verify_oidc_token(
            token=token,
            verification_key=private_key.public_key(),
            issuer=ISSUER,
            audience=AUDIENCE,
        )


def test_jwks_selects_signing_key_by_kid() -> None:
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    key_a = make_private_key()
    key_b = make_private_key()

    jwk_a = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(key_a.public_key())
    )
    jwk_a["kid"] = "key-a"
    jwk_a["alg"] = "RS256"
    jwk_a["use"] = "sig"

    jwk_b = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(key_b.public_key())
    )
    jwk_b["kid"] = "key-b"
    jwk_b["alg"] = "RS256"
    jwk_b["use"] = "sig"

    jwks_body = json.dumps(
        {
            "keys": [
                jwk_a,
                jwk_b,
            ]
        }
    ).encode("utf-8")

    class JWKSHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(jwks_body)),
            )
            self.end_headers()
            self.wfile.write(jwks_body)

        def log_message(self, format, *args) -> None:
            return

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        JWKSHandler,
    )
    thread = Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        jwks_url = (
            f"http://127.0.0.1:{server.server_port}/jwks"
        )

        token = jwt.encode(
            make_claims(),
            key_b,
            algorithm="RS256",
            headers={
                "kid": "key-b",
            },
        )

        from app.core.identity.oidc import (
            verify_oidc_token_from_jwks,
        )

        identity = verify_oidc_token_from_jwks(
            token=token,
            jwks_url=jwks_url,
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        assert identity.subject == "user-123"
        assert identity.email == "operator@example.com"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
