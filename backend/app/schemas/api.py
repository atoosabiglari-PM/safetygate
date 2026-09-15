from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class AgentRegistrationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    owner_identity: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=1000)
    model_provider: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=255)
    system_prompt_hash: str = Field(min_length=1, max_length=64)
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    memory_config: dict = Field(default_factory=dict)
    jurisdictions: list[str] = Field(default_factory=list)
    autonomy_level: str = Field(min_length=1, max_length=50)


class AgentRegistrationRead(BaseModel):
    agent_id: UUID
    agent_version_id: UUID
    organization_id: UUID
    name: str
    status: str
    version_number: int
    configuration_hash: str
    certification_status: str


class AdmissionEvaluationCreate(BaseModel):
    human_approval_actions: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)


class AdmissionEvaluationRead(BaseModel):
    organization_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    decision: str
    reasons: list[str]
    agent_status: str
    certification_status: str


class PassportIssueCreate(BaseModel):
    policy_version: str = Field(min_length=1, max_length=100)
    risk_class: str = Field(min_length=1, max_length=50)
    allowed_tools: list[str] = Field(default_factory=list)
    conditional_tools: list[str] = Field(default_factory=list)
    prohibited_tools: list[str] = Field(default_factory=list)
    human_approvers: list[str] = Field(default_factory=list)
    certification_reason: str = Field(min_length=1)


class PassportRead(BaseModel):
    passport_id: UUID
    organization_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    configuration_hash: str
    policy_version: str
    risk_class: str
    status: str
    allowed_tools: list[str]
    conditional_tools: list[str]
    prohibited_tools: list[str]
    human_approvers: list[str]
    signature_key_id: str
    issued_at: datetime


class RuntimeApprovalCreate(BaseModel):
    approval_id: str = Field(min_length=1)
    approver_identity: str = Field(min_length=1)
    approved: bool


class RuntimeAuthorizationCreate(BaseModel):
    action_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    action_name: str = Field(min_length=1)
    requested_permissions: list[str] = Field(default_factory=list)
    is_irreversible: bool = False
    risk_level: str = "LOW"
    evidence: dict = Field(default_factory=dict)
    approval: RuntimeApprovalCreate | None = None


class RuntimeAuthorizationRead(BaseModel):
    action_id: str
    passport_id: UUID
    decision: str
    reasons: list[str]
    conditions: list[str]
    audit_event_id: str
