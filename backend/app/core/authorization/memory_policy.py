from app.schemas.memory import (
    MemoryAccessRequest,
    MemoryDecision,
    MemoryDecisionResult,
    MemoryOperation,
    MemoryPolicy,
    MemoryUpdatePolicy,
)


def evaluate_memory_access(
    policy: MemoryPolicy,
    request: MemoryAccessRequest,
) -> MemoryDecisionResult:
    if request.memory_type in policy.prohibited_memory_types:
        return MemoryDecisionResult(
            decision=MemoryDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Memory type '{request.memory_type}' is explicitly prohibited."
            ],
        )

    if (
        policy.allowed_memory_types
        and request.memory_type not in policy.allowed_memory_types
    ):
        return MemoryDecisionResult(
            decision=MemoryDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Memory type '{request.memory_type}' is not allowlisted."
            ],
        )

    if (
        policy.isolated_by_user
        and request.requesting_user_id != request.memory_user_id
    ):
        return MemoryDecisionResult(
            decision=MemoryDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                "Cross-user memory access is prohibited by isolation policy."
            ],
        )

    if (
        policy.isolated_by_agent
        and request.requesting_agent_id != request.memory_agent_id
    ):
        return MemoryDecisionResult(
            decision=MemoryDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                "Cross-agent memory access is prohibited by isolation policy."
            ],
        )

    if request.memory_age_days > policy.retention_days:
        return MemoryDecisionResult(
            decision=MemoryDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                "Memory exceeds the configured retention period."
            ],
        )

    if policy.update_policy == MemoryUpdatePolicy.READ_ONLY:
        if request.operation != MemoryOperation.READ:
            return MemoryDecisionResult(
                decision=MemoryDecision.DENY,
                reasons=[
                    "Memory policy is read-only."
                ],
            )

    if policy.update_policy == MemoryUpdatePolicy.APPEND_ONLY:
        if request.operation in {
            MemoryOperation.UPDATE,
            MemoryOperation.DELETE,
        }:
            return MemoryDecisionResult(
                decision=MemoryDecision.DENY,
                reasons=[
                    "Append-only memory cannot be updated or deleted through normal agent access."
                ],
            )

    return MemoryDecisionResult(
        decision=MemoryDecision.ALLOW,
        reasons=[
            "Memory scope, retention, isolation, type, and update checks passed."
        ],
    )
