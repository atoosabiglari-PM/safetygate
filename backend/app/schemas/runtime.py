from enum import Enum

from pydantic import BaseModel, Field


class RuntimeDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENY = "DENY"
    NON_OVERRIDABLE_DENY = "NON_OVERRIDABLE_DENY"


class ActionProposal(BaseModel):
    action_id: str

    agent_id: str
    agent_version_id: str
    passport_id: str

    tool_name: str
    action_name: str
    requested_permissions: list[str] = Field(default_factory=list)

    is_irreversible: bool = False
    risk_level: str = "LOW"

    evidence: dict = Field(default_factory=dict)


class HumanApprovalContext(BaseModel):
    approval_id: str
    action_id: str
    approver_identity: str
    approved: bool


class PassportContext(BaseModel):
    status: str
    certified_configuration_hash: str
    current_configuration_hash: str

    allowed_tools: list[str] = Field(default_factory=list)
    conditional_tools: list[str] = Field(default_factory=list)
    prohibited_tools: list[str] = Field(default_factory=list)

    human_approvers: list[str] = Field(default_factory=list)


class RuntimeAuthorizationRequest(BaseModel):
    proposal: ActionProposal
    passport: PassportContext
    approval: HumanApprovalContext | None = None


class RuntimeDecisionResult(BaseModel):
    decision: RuntimeDecision
    reasons: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
