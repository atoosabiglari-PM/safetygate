from app.schemas.roles import (
    RoleAuthorizationRequest,
    RoleAuthorizationResult,
    RoleDecision,
    RuntimeRole,
)


ROLE_TOOL_ALLOWLIST: dict[RuntimeRole, set[str]] = {
    RuntimeRole.READER: {
        "read_documents",
    },
    RuntimeRole.OPERATOR: {
        "read_documents",
        "send_message",
        "deploy_service",
    },
    RuntimeRole.APPROVER: set(),
}


def authorize_role(
    request: RoleAuthorizationRequest,
) -> RoleAuthorizationResult:
    allowed_tools: set[str] = set()

    for role in request.principal.roles:
        allowed_tools.update(
            ROLE_TOOL_ALLOWLIST.get(role, set())
        )

    if request.tool_name not in allowed_tools:
        return RoleAuthorizationResult(
            decision=RoleDecision.DENY,
            reasons=[
                (
                    f"Principal '{request.principal.identity}' "
                    f"does not hold a role authorized to execute "
                    f"tool '{request.tool_name}'."
                )
            ],
        )

    return RoleAuthorizationResult(
        decision=RoleDecision.ALLOW,
        reasons=[
            "Principal role permits this tool boundary."
        ],
    )
