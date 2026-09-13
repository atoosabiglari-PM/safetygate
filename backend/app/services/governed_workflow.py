from dataclasses import dataclass

from app.core.admission.engine import evaluate_admission
from app.core.authorization.tool_gateway import execute_governed_tool
from app.schemas.admission import (
    AdmissionDecision,
    AdmissionResult,
    AgentAdmissionRequest,
)
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecision,
)
from app.schemas.tool_execution import (
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
)
from app.services.runtime_authorization import (
    RuntimeAuthorizationOutcome,
    authorize_runtime_action,
)


@dataclass(frozen=True)
class GovernedWorkflowOutcome:
    admission: AdmissionResult
    authorization: RuntimeAuthorizationOutcome | None
    execution: ToolExecutionResult | None
    audit: RuntimeAuditRecord | None


def run_governed_workflow(
    *,
    admission_request: AgentAdmissionRequest,
    runtime_request: RuntimeAuthorizationRequest,
    tool_request: ToolExecutionRequest,
) -> GovernedWorkflowOutcome:
    admission = evaluate_admission(admission_request)

    if admission.decision != AdmissionDecision.PASS:
        return GovernedWorkflowOutcome(
            admission=admission,
            authorization=None,
            execution=None,
            audit=None,
        )

    authorization = authorize_runtime_action(runtime_request)

    if authorization.decision.decision not in {
        RuntimeDecision.ALLOW,
        RuntimeDecision.ALLOW_WITH_CONDITIONS,
    }:
        return GovernedWorkflowOutcome(
            admission=admission,
            authorization=authorization,
            execution=None,
            audit=authorization.audit,
        )

    binding_reasons: list[str] = []

    if tool_request.action_id != runtime_request.proposal.action_id:
        binding_reasons.append(
            "Execution action_id does not match the authorized action_id."
        )

    if tool_request.tool_name != runtime_request.proposal.tool_name:
        binding_reasons.append(
            "Execution tool_name does not match the authorized tool_name."
        )

    if binding_reasons:
        execution = ToolExecutionResult(
            status=ToolExecutionStatus.FAILED_CLOSED,
            tool_name=tool_request.tool_name,
            reasons=binding_reasons,
            execution_attempted=False,
        )

        final_audit = authorization.audit.model_copy(
            update={
                "execution_outcome": execution.status.value,
            }
        )

        return GovernedWorkflowOutcome(
            admission=admission,
            authorization=authorization,
            execution=execution,
            audit=final_audit,
        )

    execution = execute_governed_tool(tool_request)

    final_audit = authorization.audit.model_copy(
        update={
            "execution_outcome": execution.status.value,
        }
    )

    return GovernedWorkflowOutcome(
        admission=admission,
        authorization=authorization,
        execution=execution,
        audit=final_audit,
    )
