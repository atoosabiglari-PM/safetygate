import pytest
from app.core.identity.oidc import VerifiedIdentity
from app.core.identity.principal import (
    RoleResolutionError,
    build_verified_principal,
)
from app.schemas.roles import RuntimeRole

ISSUER = "https://identity.example.com"


def test_verified_subject_receives_safetygate_assigned_role() -> None:
    identity = VerifiedIdentity(
        issuer=ISSUER,
        subject="user-123",
        email="operator@example.com",
        email_verified=True,
    )

    principal = build_verified_principal(
        identity=identity,
        role_assignments={
            (ISSUER, "user-123"): {
                RuntimeRole.OPERATOR,
            }
        },
    )

    assert principal.identity == f"{ISSUER}|user-123"
    assert principal.roles == [RuntimeRole.OPERATOR]


def test_verified_identity_without_assignment_is_rejected() -> None:
    identity = VerifiedIdentity(
        issuer=ISSUER,
        subject="user-unassigned",
        email="unknown@example.com",
        email_verified=True,
    )

    with pytest.raises(
        RoleResolutionError,
        match="no SafetyGate role assignment",
    ):
        build_verified_principal(
            identity=identity,
            role_assignments={},
        )


def test_email_does_not_grant_another_subjects_role() -> None:
    authorized_identity = VerifiedIdentity(
        issuer=ISSUER,
        subject="authorized-user",
        email="operator@example.com",
        email_verified=True,
    )

    impersonating_identity = VerifiedIdentity(
        issuer=ISSUER,
        subject="different-user",
        email="operator@example.com",
        email_verified=True,
    )

    assignments = {
        (ISSUER, "authorized-user"): {
            RuntimeRole.OPERATOR,
        }
    }

    authorized = build_verified_principal(
        identity=authorized_identity,
        role_assignments=assignments,
    )

    assert authorized.roles == [RuntimeRole.OPERATOR]

    with pytest.raises(RoleResolutionError):
        build_verified_principal(
            identity=impersonating_identity,
            role_assignments=assignments,
        )
