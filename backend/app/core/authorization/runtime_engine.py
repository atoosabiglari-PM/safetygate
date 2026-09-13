from app.core.admission.tool_registry import TOOL_PERMISSION_REQUIREMENTS
from app.core.recertification.passport_validator import (
    PassportValidationStatus,
    validate_passport,
)
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)


def evaluate_runtime_action(
    request: RuntimeAuthorizationRequest,
) -> RuntimeDecisionResult:
    proposal = request.proposal
    passport = request.passport

    passport_result = validate_passport(
        passport_status=passport.status,
        passport_configuration_hash=passport.certified_configuration_hash,
        current_configuration_hash=passport.current_configuration_hash,
    )

    if passport_result.status == PassportValidationStatus.INVALID:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[passport_result.reason],
        )

    if passport_result.status == PassportValidationStatus.RECERTIFICATION_REQUIRED:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[passport_result.reason],
        )

    if proposal.tool_name in passport.prohibited_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' is prohibited by the Safety Passport."
            ],
        )

    passport_tools = set(passport.allowed_tools) | set(passport.conditional_tools)

    if proposal.tool_name not in passport_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' is not authorized by the Safety Passport."
            ],
        )

    required_permissions = TOOL_PERMISSION_REQUIREMENTS.get(proposal.tool_name)

    if required_permissions is None:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' has no registered permission contract."
            ],
        )

    missing_permissions = required_permissions - set(proposal.requested_permissions)

    if missing_permissions:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                "Missing required permission(s): "
                + ", ".join(sorted(missing_permissions))
            ],
        )

    if proposal.tool_name in passport.conditional_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
            reasons=[
                f"Tool '{proposal.tool_name}' is conditionally authorized by the Safety Passport."
            ],
            conditions=[
                "Record full audit evidence.",
                "Verify execution result.",
            ],
        )

    risk_level = proposal.risk_level.upper()

    if risk_level == "HIGH" and proposal.is_irreversible:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.HUMAN_REVIEW_REQUIRED,
            reasons=[
                "High-risk irreversible action requires human approval."
            ],
        )

    if risk_level == "MEDIUM":
        return RuntimeDecisionResult(
            decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
            reasons=[
                "Medium-risk action may proceed under additional controls."
            ],
            conditions=[
                "Record full audit evidence.",
                "Verify execution result.",
            ],
        )

    return RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=[
            "Passport, configuration, tool, permission, and runtime checks passed."
        ],
    )
