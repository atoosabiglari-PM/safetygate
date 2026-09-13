from dataclasses import dataclass

from app.schemas.audit import RuntimeAuditRecord
from app.schemas.tool_execution import (
    ToolExecutionResult,
    ToolExecutionStatus,
)


SUPPORTED_RUNTIME_CONDITIONS = {
    "Record full audit evidence.",
    "Verify execution result.",
}


@dataclass(frozen=True)
class ConditionEnforcementResult:
    satisfied: bool
    reasons: list[str]


def validate_supported_conditions(
    conditions: list[str],
) -> ConditionEnforcementResult:
    unsupported = [
        condition
        for condition in conditions
        if condition not in SUPPORTED_RUNTIME_CONDITIONS
    ]

    if unsupported:
        return ConditionEnforcementResult(
            satisfied=False,
            reasons=[
                "Unsupported runtime condition: " + condition
                for condition in unsupported
            ],
        )

    return ConditionEnforcementResult(
        satisfied=True,
        reasons=["All runtime conditions are recognized."],
    )


def verify_execution_conditions(
    *,
    conditions: list[str],
    audit: RuntimeAuditRecord,
    execution: ToolExecutionResult,
) -> ConditionEnforcementResult:
    reasons: list[str] = []

    if "Record full audit evidence." in conditions:
        if not audit.action_id or not audit.tool_name or not audit.decision:
            reasons.append(
                "Required audit evidence was incomplete."
            )

    if "Verify execution result." in conditions:
        acceptable_statuses = {
            ToolExecutionStatus.EXECUTED,
            ToolExecutionStatus.FALLBACK_EXECUTED,
            ToolExecutionStatus.DUPLICATE_SUPPRESSED,
        }

        if execution.status not in acceptable_statuses:
            reasons.append(
                "Execution result did not satisfy verification requirements."
            )

    if reasons:
        return ConditionEnforcementResult(
            satisfied=False,
            reasons=reasons,
        )

    return ConditionEnforcementResult(
        satisfied=True,
        reasons=["All runtime conditions were satisfied."],
    )
