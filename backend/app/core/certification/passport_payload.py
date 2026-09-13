import json
from datetime import datetime
from typing import Any

SIGNED_PASSPORT_FIELDS = (
    "passport_id",
    "organization_id",
    "agent_version_id",
    "configuration_hash",
    "policy_version",
    "risk_class",
    "allowed_tools",
    "conditional_tools",
    "prohibited_tools",
    "human_approvers",
    "issued_at",
)

SET_LIKE_FIELDS = {
    "allowed_tools",
    "conditional_tools",
    "prohibited_tools",
    "human_approvers",
}


def _canonicalize_value(name: str, value: Any) -> Any:
    if name in SET_LIKE_FIELDS:
        return sorted(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def build_passport_payload(**fields: Any) -> bytes:
    missing = [
        name
        for name in SIGNED_PASSPORT_FIELDS
        if name not in fields
    ]

    if missing:
        raise ValueError(
            "Missing signed passport field(s): " + ", ".join(missing)
        )

    payload = {
        name: _canonicalize_value(name, fields[name])
        for name in SIGNED_PASSPORT_FIELDS
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return canonical.encode("utf-8")


def build_runtime_passport_payload(passport: Any) -> bytes:
    return build_passport_payload(
        passport_id=passport.passport_id,
        organization_id=passport.organization_id,
        agent_version_id=passport.agent_version_id,
        configuration_hash=passport.certified_configuration_hash,
        policy_version=passport.policy_version,
        risk_class=passport.risk_class,
        allowed_tools=passport.allowed_tools,
        conditional_tools=passport.conditional_tools,
        prohibited_tools=passport.prohibited_tools,
        human_approvers=passport.human_approvers,
        issued_at=passport.issued_at,
    )
