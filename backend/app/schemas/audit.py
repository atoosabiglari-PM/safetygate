from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeAuditRecord(BaseModel):
    event_id: str
    timestamp: datetime

    action_id: str
    agent_id: str
    agent_version_id: str
    passport_id: str

    tool_name: str
    action_name: str
    requested_permissions: list[str] = Field(default_factory=list)

    passport_status: str
    certified_configuration_hash: str
    current_configuration_hash: str

    approval_id: str | None = None
    approver_identity: str | None = None
    human_approved: bool | None = None

    decision: str
    reasons: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)

    evidence: dict[str, Any] = Field(default_factory=dict)

    principal_identity: str | None = None
    principal_roles: list[str] = Field(default_factory=list)
    enforcement_reasons: list[str] = Field(default_factory=list)

    policy_rule_id: str | None = None
    policy_authority: str | None = None
    policy_source_name: str | None = None
    policy_source_version: str | None = None
    policy_source_reference: str | None = None
    policy_considered_rules: list[dict[str, Any]] = Field(
        default_factory=list
    )

    execution_outcome: str | None = None
