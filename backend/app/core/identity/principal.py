from collections.abc import Collection, Mapping

from app.core.identity.oidc import VerifiedIdentity
from app.schemas.roles import PrincipalContext, RuntimeRole


class RoleResolutionError(ValueError):
    """Raised when a verified identity has no trusted SafetyGate role assignment."""


RoleAssignmentKey = tuple[str, str]


def build_verified_principal(
    *,
    identity: VerifiedIdentity,
    role_assignments: Mapping[
        RoleAssignmentKey,
        Collection[RuntimeRole],
    ],
) -> PrincipalContext:
    key = (identity.issuer, identity.subject)
    assigned_roles = list(role_assignments.get(key, ()))

    if not assigned_roles:
        raise RoleResolutionError(
            "Verified identity has no SafetyGate role assignment."
        )

    return PrincipalContext(
        identity=f"{identity.issuer}|{identity.subject}",
        roles=assigned_roles,
    )
