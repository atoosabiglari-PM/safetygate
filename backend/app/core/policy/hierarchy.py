from dataclasses import dataclass
from enum import IntEnum


class PolicyAuthority(IntEnum):
    MANDATORY_LAW = 1
    FUNDAMENTAL_RIGHTS = 2
    AI_GOVERNANCE_STANDARD = 3
    SECURITY_STANDARD = 4
    ORGANIZATION_POLICY = 5
    AGENT_IDENTITY_AND_PERMISSIONS = 6
    HUMAN_AUTHORITY = 7
    RUNTIME_EVIDENCE = 8


@dataclass(frozen=True)
class PolicyProvenance:
    rule_id: str
    authority: PolicyAuthority
    source_name: str
    source_version: str
    source_reference: str | None = None


def higher_authority(
    left: PolicyAuthority,
    right: PolicyAuthority,
) -> PolicyAuthority:
    return left if left.value < right.value else right
