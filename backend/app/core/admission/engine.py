from app.core.admission.tool_registry import TOOL_PERMISSION_REQUIREMENTS
from app.schemas.admission import (
    AdmissionDecision,
    AdmissionResult,
    AgentAdmissionRequest,
)


HIGH_RISK_AUTONOMY_LEVELS = {"HIGH", "FULL", "UNBOUNDED"}


def evaluate_admission(request: AgentAdmissionRequest) -> AdmissionResult:
    non_overridable_reasons: list[str] = []
    correctable_reasons: list[str] = []

    if not request.jurisdictions:
        non_overridable_reasons.append(
            "Agent cannot operate without at least one declared jurisdiction."
        )

    prohibited_conflicts = set(request.tools) & set(request.prohibited_actions)

    if prohibited_conflicts:
        non_overridable_reasons.append(
            "Agent requested a capability that is explicitly prohibited: "
            + ", ".join(sorted(prohibited_conflicts))
        )

    declared_permissions = set(request.permissions)

    for tool in request.tools:
        required_permissions = TOOL_PERMISSION_REQUIREMENTS.get(tool)

        if required_permissions is None:
            non_overridable_reasons.append(
                f"Tool '{tool}' has no registered permission contract."
            )
            continue

        missing_permissions = required_permissions - declared_permissions

        if missing_permissions:
            non_overridable_reasons.append(
                f"Tool '{tool}' requires missing permission(s): "
                + ", ".join(sorted(missing_permissions))
            )

    if request.autonomy_level.upper() in HIGH_RISK_AUTONOMY_LEVELS:
        if not request.human_approval_actions:
            correctable_reasons.append(
                "High-autonomy agents must declare actions requiring human approval."
            )

    if non_overridable_reasons:
        return AdmissionResult(
            decision=AdmissionDecision.NON_OVERRIDABLE_FAIL,
            reasons=non_overridable_reasons + correctable_reasons,
        )

    if correctable_reasons:
        return AdmissionResult(
            decision=AdmissionDecision.FAIL,
            reasons=correctable_reasons,
        )

    return AdmissionResult(
        decision=AdmissionDecision.PASS,
        reasons=[
            "Agent identity, ownership, purpose, autonomy, jurisdiction, "
            "tool permissions, and declared boundaries passed admission checks."
        ],
    )
