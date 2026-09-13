from enum import Enum

from pydantic import BaseModel, Field


class RuntimeRole(str, Enum):
    READER = "READER"
    OPERATOR = "OPERATOR"
    APPROVER = "APPROVER"


class RoleDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class PrincipalContext(BaseModel):
    identity: str = Field(min_length=1)
    roles: list[RuntimeRole] = Field(min_length=1)


class RoleAuthorizationRequest(BaseModel):
    principal: PrincipalContext
    tool_name: str = Field(min_length=1)


class RoleAuthorizationResult(BaseModel):
    decision: RoleDecision
    reasons: list[str] = Field(default_factory=list)
