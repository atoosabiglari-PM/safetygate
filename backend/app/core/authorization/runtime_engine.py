from app.core.admission.tool_registry import TOOL_PERMISSION_REQUIREMENTS
from app.core.certification.kms_verifier import verify_passport_signature
from app.core.certification.passport_payload import build_runtime_passport_payload
from app.core.recertification.passport_validator import (
    PassportValidationStatus,
    SignatureVerifier,
    validate_passport,
)
from app.schemas.runtime import (
    RuntimeAuthorizationRequest,
    RuntimeDecision,
    RuntimeDecisionResult,
)


def evaluate_runtime_action(
    request: RuntimeAuthorizationRequest,
    *,
    signature_verifier: SignatureVerifier = verify_passport_signature,
) -> RuntimeDecisionResult:
    proposal = request.proposal
    passport = request.passport
    approval = request.approval

    # 1. Verify and validate Safety Passport before considering any approval.
    signed_payload = build_runtime_passport_payload(passport)

    passport_result = validate_passport(
        passport_status=passport.status,
        passport_configuration_hash=passport.certified_configuration_hash,
        current_configuration_hash=passport.current_configuration_hash,
        signed_payload=signed_payload,
        signature=passport.signature,
        signature_key_id=passport.signature_key_id,
        signature_verifier=signature_verifier,
    )

    if passport_result.status == PassportValidationStatus.INVALID:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[passport_result.reason],
        )

    if passport_result.status == PassportValidationStatus.RECERTIFICATION_REQUIRED:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[passport_result.reason],
        )

    # 2. Bind the proposed action to the signed Safety Passport.
    if proposal.passport_id != passport.passport_id:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                (
                    "Proposed action passport_id does not match "
                    "the signed Safety Passport."
                )
            ],
        )

    if proposal.agent_version_id != passport.agent_version_id:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                (
                    "Proposed action agent_version_id does not match "
                    "the signed Safety Passport."
                )
            ],
        )

    # 3. Enforce passport tool boundaries.
    if proposal.tool_name in passport.prohibited_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' is prohibited by the Safety Passport."
            ],
        )

    passport_tools = set(passport.allowed_tools) | set(passport.conditional_tools)

    if proposal.tool_name not in passport_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' is not authorized by the Safety Passport."
            ],
        )

    # 4. Enforce deterministic permission contract.
    required_permissions = TOOL_PERMISSION_REQUIREMENTS.get(proposal.tool_name)

    if required_permissions is None:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                f"Tool '{proposal.tool_name}' has no registered permission contract."
            ],
        )

    missing_permissions = required_permissions - set(proposal.requested_permissions)

    if missing_permissions:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
            reasons=[
                "Missing required permission(s): "
                + ", ".join(sorted(missing_permissions))
            ],
        )

    # 5. High-risk irreversible actions require verified human approval.
    risk_level = proposal.risk_level.upper()

    if risk_level == "HIGH" and proposal.is_irreversible:
        if approval is None:
            return RuntimeDecisionResult(
                decision=RuntimeDecision.HUMAN_REVIEW_REQUIRED,
                reasons=[
                    "High-risk irreversible action requires human approval."
                ],
            )

        if approval.action_id != proposal.action_id:
            return RuntimeDecisionResult(
                decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
                reasons=[
                    "Human approval does not match the proposed action."
                ],
            )

        if approval.approver_identity not in passport.human_approvers:
            return RuntimeDecisionResult(
                decision=RuntimeDecision.NON_OVERRIDABLE_DENY,
                reasons=[
                    "Human approval was issued by an unauthorized approver."
                ],
            )

        if not approval.approved:
            return RuntimeDecisionResult(
                decision=RuntimeDecision.DENY,
                reasons=[
                    "Authorized human reviewer rejected the proposed action."
                ],
            )

    # 6. Passport conditions still apply even after valid approval.
    if proposal.tool_name in passport.conditional_tools:
        return RuntimeDecisionResult(
            decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
            reasons=[
                f"Tool '{proposal.tool_name}' is conditionally authorized by the Safety Passport."
            ],
            conditions=[
                "Record full audit evidence.",
                "Verify execution result.",
            ],
        )

    if risk_level == "MEDIUM":
        return RuntimeDecisionResult(
            decision=RuntimeDecision.ALLOW_WITH_CONDITIONS,
            reasons=[
                "Medium-risk action may proceed under additional controls."
            ],
            conditions=[
                "Record full audit evidence.",
                "Verify execution result.",
            ],
        )

    return RuntimeDecisionResult(
        decision=RuntimeDecision.ALLOW,
        reasons=[
            "Passport, configuration, tool, permission, risk, and approval checks passed."
        ],
    )
