from dataclasses import dataclass
from typing import Any

from app.core.authorization.tool_gateway import ToolExecutor
from app.schemas.admission import AgentAdmissionRequest
from app.schemas.roles import PrincipalContext
from app.schemas.runtime import (
    ActionProposal,
    PassportContext,
    RuntimeAuthorizationRequest,
)
from app.schemas.tool_execution import ToolExecutionRequest
from app.services.governed_workflow import (
    GovernedWorkflowOutcome,
    run_governed_workflow,
)


@dataclass(frozen=True)
class AgentToolProposal:
    action_id: str
    agent_id: str
    agent_version_id: str
    tool_name: str
    action_name: str
    requested_permissions: tuple[str, ...]
    arguments: dict[str, Any]
    risk_level: str = "LOW"
    is_irreversible: bool = False


def run_agent_proposal(
    *,
    proposal: AgentToolProposal,
    admission_request: AgentAdmissionRequest,
    passport: PassportContext,
    principal: PrincipalContext,
    tool_executor: ToolExecutor,
) -> GovernedWorkflowOutcome:
    """Route an agent proposal through SafetyGate before any tool execution."""

    runtime_request = RuntimeAuthorizationRequest(
        proposal=ActionProposal(
            action_id=proposal.action_id,
            agent_id=proposal.agent_id,
            agent_version_id=proposal.agent_version_id,
            passport_id=passport.passport_id,
            tool_name=proposal.tool_name,
            action_name=proposal.action_name,
            requested_permissions=list(
                proposal.requested_permissions
            ),
            is_irreversible=proposal.is_irreversible,
            risk_level=proposal.risk_level,
            evidence={
                "source": "agent-proposal",
            },
        ),
        passport=passport,
    )

    tool_request = ToolExecutionRequest(
        action_id=proposal.action_id,
        idempotency_key=f"agent:{proposal.action_id}",
        tool_name=proposal.tool_name,
        arguments=proposal.arguments,
    )

    return run_governed_workflow(
        admission_request=admission_request,
        runtime_request=runtime_request,
        tool_request=tool_request,
        principal=principal,
        tool_executor=tool_executor,
    )
