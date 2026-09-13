from dataclasses import dataclass
from typing import Any

import jwt


class OIDCVerificationError(ValueError):
    """Raised when identity evidence cannot be cryptographically verified."""


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool | None


def verify_oidc_token(
    *,
    token: str,
    verification_key: Any,
    issuer: str,
    audience: str,
    algorithm: str = "RS256",
) -> VerifiedIdentity:
    try:
        claims = jwt.decode(
            token,
            verification_key,
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
            options={
                "require": [
                    "iss",
                    "sub",
                    "aud",
                    "iat",
                    "exp",
                ]
            },
        )
    except jwt.PyJWTError as exc:
        raise OIDCVerificationError(
            "OIDC token verification failed."
        ) from exc

    subject = claims["sub"]

    if not isinstance(subject, str) or not subject.strip():
        raise OIDCVerificationError(
            "OIDC token subject is invalid."
        )

    email = claims.get("email")
    if email is not None and not isinstance(email, str):
        raise OIDCVerificationError(
            "OIDC email claim is invalid."
        )

    email_verified = claims.get("email_verified")
    if (
        email_verified is not None
        and not isinstance(email_verified, bool)
    ):
        raise OIDCVerificationError(
            "OIDC email_verified claim is invalid."
        )

    return VerifiedIdentity(
        issuer=claims["iss"],
        subject=subject,
        email=email,
        email_verified=email_verified,
    )


def verify_oidc_token_from_jwks(
    *,
    token: str,
    jwks_url: str,
    issuer: str,
    audience: str,
    algorithm: str = "RS256",
) -> VerifiedIdentity:
    try:
        jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except jwt.PyJWTError as exc:
        raise OIDCVerificationError(
            "OIDC signing key discovery failed."
        ) from exc

    return verify_oidc_token(
        token=token,
        verification_key=signing_key.key,
        issuer=issuer,
        audience=audience,
        algorithm=algorithm,
    )
