from enum import Enum

from pydantic import BaseModel, Field


class MemoryScope(str, Enum):
    SESSION = "SESSION"
    AGENT = "AGENT"
    USER = "USER"
    ORGANIZATION = "ORGANIZATION"


class MemoryUpdatePolicy(str, Enum):
    READ_ONLY = "READ_ONLY"
    APPEND_ONLY = "APPEND_ONLY"
    CONTROLLED_UPDATE = "CONTROLLED_UPDATE"


class MemoryOperation(str, Enum):
    READ = "READ"
    APPEND = "APPEND"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class MemoryDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NON_OVERRIDABLE_DENY = "NON_OVERRIDABLE_DENY"


class MemoryPolicy(BaseModel):
    scope: MemoryScope
    retention_days: int = Field(ge=0)
    update_policy: MemoryUpdatePolicy

    isolated_by_user: bool = True
    isolated_by_agent: bool = True

    allowed_memory_types: list[str] = Field(default_factory=list)
    prohibited_memory_types: list[str] = Field(default_factory=list)


class MemoryAccessRequest(BaseModel):
    requesting_agent_id: str
    memory_agent_id: str

    requesting_user_id: str
    memory_user_id: str

    memory_type: str
    memory_age_days: int = Field(ge=0)

    operation: MemoryOperation


class MemoryDecisionResult(BaseModel):
    decision: MemoryDecision
    reasons: list[str] = Field(default_factory=list)
