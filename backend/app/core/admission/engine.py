from app.schemas.admission import (
    AdmissionDecision,
    AdmissionResult,
    AgentAdmissionRequest,
)


HIGH_RISK_AUTONOMY_LEVELS = {"HIGH", "FULL", "UNBOUNDED"}


def evaluate_admission(request: AgentAdmissionRequest) -> AdmissionResult:
    reasons: list[str] = []

    if not request.owner_identity.strip():
        reasons.append("Agent must have an accountable owner.")

    if not request.purpose.strip():
        reasons.append("Agent must declare a valid purpose.")

    if request.autonomy_level.upper() in HIGH_RISK_AUTONOMY_LEVELS:
        if not request.human_approval_actions:
            reasons.append(
                "High-autonomy agents must declare actions requiring human approval."
            )

    if set(request.tools) & set(request.prohibited_actions):
        reasons.append(
            "An agent cannot request tools that are explicitly prohibited."
        )

    if reasons:
        return AdmissionResult(
            decision=AdmissionDecision.FAIL,
            reasons=reasons,
        )

    return AdmissionResult(
        decision=AdmissionDecision.PASS,
        reasons=[
            "Agent identity, ownership, purpose, autonomy, and declared boundaries passed admission checks."
        ],
    )
