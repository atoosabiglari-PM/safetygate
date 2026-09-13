from enum import Enum

from pydantic import BaseModel, Field


class AdmissionDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class AgentAdmissionRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    owner_identity: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=1000)

    model_provider: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=255)

    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)

    autonomy_level: str

    human_approval_actions: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)


class AdmissionResult(BaseModel):
    decision: AdmissionDecision
    reasons: list[str] = Field(default_factory=list)
