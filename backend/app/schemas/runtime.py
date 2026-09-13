from enum import Enum

from pydantic import BaseModel, Field


class RuntimeDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENY = "DENY"
    NON_OVERRIDABLE_DENY = "NON_OVERRIDABLE_DENY"


class ActionProposal(BaseModel):
    agent_id: str
    agent_version_id: str
    passport_id: str

    tool_name: str
    action_name: str
    requested_permissions: list[str] = Field(default_factory=list)

    is_irreversible: bool = False
    risk_level: str = "LOW"

    evidence: dict = Field(default_factory=dict)


class RuntimeDecisionResult(BaseModel):
    decision: RuntimeDecision
    reasons: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
