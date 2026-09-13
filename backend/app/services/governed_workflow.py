from dataclasses import dataclass, replace

from app.core.admission.engine import evaluate_admission
from app.core.authorization.condition_enforcement import (
    validate_supported_conditions,
    verify_execution_conditions,
)
from app.core.authorization.role_policy import authorize_role
from app.core.authorization.tool_gateway import execute_governed_tool
from app.schemas.admission import (
    AdmissionDecision,
    AdmissionResult,
    AgentAdmissionRequest,
)
from app.schemas.audit import RuntimeAuditRecord
from app.schemas.roles import (
    PrincipalContext,
    RoleAuthorizationRequest,
    RoleDecision,
)
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
    principal: PrincipalContext,
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

    authorization = replace(
        authorization,
        audit=authorization.audit.model_copy(
            update={
                "principal_identity": principal.identity,
                "principal_roles": [
                    role.value for role in principal.roles
                ],
            }
        ),
    )

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
                "enforcement_reasons": binding_reasons,
            }
        )

        return GovernedWorkflowOutcome(
            admission=admission,
            authorization=authorization,
            execution=execution,
            audit=final_audit,
        )

    role_authorization = authorize_role(
        RoleAuthorizationRequest(
            principal=principal,
            tool_name=runtime_request.proposal.tool_name,
        )
    )

    if role_authorization.decision == RoleDecision.DENY:
        execution = ToolExecutionResult(
            status=ToolExecutionStatus.FAILED_CLOSED,
            tool_name=tool_request.tool_name,
            reasons=role_authorization.reasons,
            execution_attempted=False,
        )

        final_audit = authorization.audit.model_copy(
            update={
                "execution_outcome": execution.status.value,
                "enforcement_reasons": role_authorization.reasons,
            }
        )

        return GovernedWorkflowOutcome(
            admission=admission,
            authorization=authorization,
            execution=execution,
            audit=final_audit,
        )

    conditions = authorization.decision.conditions

    if authorization.decision.decision == RuntimeDecision.ALLOW_WITH_CONDITIONS:
        supported = validate_supported_conditions(conditions)

        if not supported.satisfied:
            execution = ToolExecutionResult(
                status=ToolExecutionStatus.FAILED_CLOSED,
                tool_name=tool_request.tool_name,
                reasons=supported.reasons,
                execution_attempted=False,
            )

            final_audit = authorization.audit.model_copy(
                update={"execution_outcome": execution.status.value}
            )

            return GovernedWorkflowOutcome(
                admission=admission,
                authorization=authorization,
                execution=execution,
                audit=final_audit,
            )

    execution = execute_governed_tool(tool_request)

    final_audit = authorization.audit.model_copy(
        update={"execution_outcome": execution.status.value}
    )

    if authorization.decision.decision == RuntimeDecision.ALLOW_WITH_CONDITIONS:
        verification = verify_execution_conditions(
            conditions=conditions,
            audit=final_audit,
            execution=execution,
        )

        if not verification.satisfied:
            execution = ToolExecutionResult(
                status=ToolExecutionStatus.HUMAN_REVIEW_REQUIRED,
                tool_name=tool_request.tool_name,
                output=execution.output,
                reasons=verification.reasons,
                execution_attempted=execution.execution_attempted,
                fallback_used=execution.fallback_used,
            )

            final_audit = final_audit.model_copy(
                update={"execution_outcome": execution.status.value}
            )

    return GovernedWorkflowOutcome(
        admission=admission,
        authorization=authorization,
        execution=execution,
        audit=final_audit,
    )
