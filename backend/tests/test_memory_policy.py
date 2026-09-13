from app.core.authorization.memory_policy import evaluate_memory_access
from app.schemas.memory import (
    MemoryAccessRequest,
    MemoryDecision,
    MemoryOperation,
    MemoryPolicy,
    MemoryScope,
    MemoryUpdatePolicy,
)


def make_policy(**overrides) -> MemoryPolicy:
    data = {
        "scope": MemoryScope.USER,
        "retention_days": 30,
        "update_policy": MemoryUpdatePolicy.CONTROLLED_UPDATE,
        "isolated_by_user": True,
        "isolated_by_agent": True,
        "allowed_memory_types": ["preference", "task_context"],
        "prohibited_memory_types": ["credential", "secret"],
    }
    data.update(overrides)
    return MemoryPolicy(**data)


def make_request(**overrides) -> MemoryAccessRequest:
    data = {
        "requesting_agent_id": "agent-001",
        "memory_agent_id": "agent-001",
        "requesting_user_id": "user-001",
        "memory_user_id": "user-001",
        "memory_type": "preference",
        "memory_age_days": 5,
        "operation": MemoryOperation.READ,
    }
    data.update(overrides)
    return MemoryAccessRequest(**data)


def test_valid_memory_access_is_allowed() -> None:
    result = evaluate_memory_access(make_policy(), make_request())
    assert result.decision == MemoryDecision.ALLOW


def test_cross_user_memory_access_is_non_overridable_denied() -> None:
    result = evaluate_memory_access(
        make_policy(),
        make_request(memory_user_id="user-002"),
    )
    assert result.decision == MemoryDecision.NON_OVERRIDABLE_DENY


def test_cross_agent_memory_access_is_non_overridable_denied() -> None:
    result = evaluate_memory_access(
        make_policy(),
        make_request(memory_agent_id="agent-002"),
    )
    assert result.decision == MemoryDecision.NON_OVERRIDABLE_DENY


def test_expired_memory_is_non_overridable_denied() -> None:
    result = evaluate_memory_access(
        make_policy(),
        make_request(memory_age_days=31),
    )
    assert result.decision == MemoryDecision.NON_OVERRIDABLE_DENY


def test_prohibited_memory_type_is_non_overridable_denied() -> None:
    result = evaluate_memory_access(
        make_policy(),
        make_request(memory_type="secret"),
    )
    assert result.decision == MemoryDecision.NON_OVERRIDABLE_DENY


def test_non_allowlisted_memory_type_is_non_overridable_denied() -> None:
    result = evaluate_memory_access(
        make_policy(),
        make_request(memory_type="unknown_type"),
    )
    assert result.decision == MemoryDecision.NON_OVERRIDABLE_DENY


def test_read_only_policy_blocks_write() -> None:
    result = evaluate_memory_access(
        make_policy(update_policy=MemoryUpdatePolicy.READ_ONLY),
        make_request(operation=MemoryOperation.UPDATE),
    )
    assert result.decision == MemoryDecision.DENY


def test_append_only_policy_blocks_update() -> None:
    result = evaluate_memory_access(
        make_policy(update_policy=MemoryUpdatePolicy.APPEND_ONLY),
        make_request(operation=MemoryOperation.UPDATE),
    )
    assert result.decision == MemoryDecision.DENY
