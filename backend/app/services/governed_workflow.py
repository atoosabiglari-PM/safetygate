from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from app.core.admission.engine import evaluate_admission
from app.core.audit.persistence import (
    save_approval_evidence,
    save_runtime_audit_entry,
)
from app.core.authorization.condition_enforcement import (
    validate_supported_conditions,
    verify_execution_conditions,
)
from app.core.authorization.role_policy import authorize_role
from app.core.authorization.tool_gateway import (
    ToolExecutor,
    execute_governed_tool,
)
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


def _persist_runtime_evidence(
    *,
    session: Session | None,
    runtime_request: RuntimeAuthorizationRequest,
    audit: RuntimeAuditRecord,
) -> None:
    if session is None:
        return

    if runtime_request.approval is not None:
        save_approval_evidence(session, runtime_request.approval)

    save_runtime_audit_entry(session, audit)


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
    tool_executor: ToolExecutor | None = None,
    session: Session | None = None,
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
        _persist_runtime_evidence(
            session=session,
            runtime_request=runtime_request,
            audit=authorization.audit,
        )

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

        _persist_runtime_evidence(
            session=session,
            runtime_request=runtime_request,
            audit=final_audit,
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

        _persist_runtime_evidence(
            session=session,
            runtime_request=runtime_request,
            audit=final_audit,
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

            _persist_runtime_evidence(
                session=session,
                runtime_request=runtime_request,
                audit=final_audit,
            )

            return GovernedWorkflowOutcome(
                admission=admission,
                authorization=authorization,
                execution=execution,
                audit=final_audit,
            )

    execution = execute_governed_tool(
        tool_request,
        executor=tool_executor,
        session=session,
    )

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

    _persist_runtime_evidence(
        session=session,
        runtime_request=runtime_request,
        audit=final_audit,
    )

    return GovernedWorkflowOutcome(
        admission=admission,
        authorization=authorization,
        execution=execution,
        audit=final_audit,
    )
