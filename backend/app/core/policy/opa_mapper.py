from typing import Any

from app.core.policy.hierarchy import (
    PolicyAuthority,
    PolicyProvenance,
)
from app.core.policy.resolver import (
    PolicyResolution,
    PolicyRuleDecision,
    resolve_policy_decisions,
)
from app.schemas.runtime import RuntimeDecision


class OpaPolicyMappingError(ValueError):
    """Raised when OPA policy output cannot be mapped safely."""


def _required_nonempty_string(
    rule: dict[str, Any],
    field: str,
) -> str:
    value = rule.get(field)

    if not isinstance(value, str) or not value.strip():
        raise OpaPolicyMappingError(
            f"OPA rule field '{field}' must be a non-empty string."
        )

    return value


def _parse_conditions(
    rule: dict[str, Any],
) -> tuple[str, ...]:
    value = rule.get("conditions", [])

    if not isinstance(value, list):
        raise OpaPolicyMappingError(
            "OPA rule field 'conditions' must be a list."
        )

    if not all(
        isinstance(item, str) and item.strip()
        for item in value
    ):
        raise OpaPolicyMappingError(
            "OPA rule conditions must be non-empty strings."
        )

    return tuple(value)


def map_opa_rule_decision(
    rule: dict[str, Any],
) -> PolicyRuleDecision:
    rule_id = _required_nonempty_string(
        rule,
        "rule_id",
    )
    authority_name = _required_nonempty_string(
        rule,
        "authority",
    )
    source_name = _required_nonempty_string(
        rule,
        "source_name",
    )
    source_version = _required_nonempty_string(
        rule,
        "source_version",
    )
    decision_name = _required_nonempty_string(
        rule,
        "decision",
    )
    reason = _required_nonempty_string(
        rule,
        "reason",
    )

    source_reference = rule.get("source_reference")

    if (
        source_reference is not None
        and (
            not isinstance(source_reference, str)
            or not source_reference.strip()
        )
    ):
        raise OpaPolicyMappingError(
            "OPA rule field 'source_reference' must be "
            "null or a non-empty string."
        )

    try:
        authority = PolicyAuthority[authority_name]
    except KeyError as exc:
        raise OpaPolicyMappingError(
            f"Unknown OPA policy authority: {authority_name}"
        ) from exc

    try:
        decision = RuntimeDecision(decision_name)
    except ValueError as exc:
        raise OpaPolicyMappingError(
            f"Unknown OPA runtime decision: {decision_name}"
        ) from exc

    return PolicyRuleDecision(
        provenance=PolicyProvenance(
            rule_id=rule_id,
            authority=authority,
            source_name=source_name,
            source_version=source_version,
            source_reference=source_reference,
        ),
        decision=decision,
        reason=reason,
        conditions=_parse_conditions(rule),
    )


def build_policy_resolution_from_opa(
    rules: tuple[dict[str, Any], ...],
) -> PolicyResolution:
    if not rules:
        raise OpaPolicyMappingError(
            "At least one OPA policy rule is required."
        )

    decisions = sorted(
        (
            map_opa_rule_decision(rule)
            for rule in rules
        ),
        key=lambda item: (
            item.provenance.authority.value,
            item.provenance.rule_id,
        ),
    )

    return resolve_policy_decisions(decisions)
