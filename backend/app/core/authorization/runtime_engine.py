from app.core.admission.tool_registry import TOOL_PERMISSION_REQUIREMENTS
from app.schemas.runtime import (
    ActionProposal,
    RuntimeDecision,
    RuntimeDecisionResult,
)


PROHIBITED_RUNTIME_TOOLS = {"delete_records"}


def evaluate_runtime_action(proposal: ActionProposal) -> RuntimeDecisionResult:
    required_permissions = TOOL_PERMISSION_REQUIREMENTS.get(proposal.tool_name)

    if required_permissions is None:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' has no registered permission contract."
            ],
        )

    if proposal.tool_name in PROHIBITED_RUNTIME_TOOLS:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' is prohibited at runtime."
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
            "Runtime authorization checks passed."
        ],
    )
