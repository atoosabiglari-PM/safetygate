# SafetyGate MVP Demo Script

## Demo Goal

Show that SafetyGate independently certifies an AI agent and governs consequential actions at runtime.

## 1. Register Agent

Show:
- agent identity
- version
- configuration
- tools
- permissions
- owner

Message:
"SafetyGate first establishes exactly what agent is requesting authority."

## 2. Admission

Run SafetyGate admission.

Expected:

`PASS`

Explain:
"An agent cannot receive a Safety Passport until it passes admission."

## 3. Certification

Issue the Safety Passport.

Show:
- agent version
- configuration hash
- policy version
- allowed tools
- permissions
- authorized human approvers
- KMS signing key reference
- ACTIVE status

Message:
"The Safety Passport cryptographically binds certification to this exact agent configuration."

## 4. Normal Runtime Authorization

Submit a permitted action.

Show:

`ALLOW`

Message:
"Certification alone does not bypass runtime governance. Every consequential action is re-evaluated."

## 5. High-Risk Action

Submit a HIGH-risk irreversible action.

Show:

`HUMAN_REVIEW_REQUIRED`

Message:
"The agent cannot approve itself."

## 6. Forged Approval Attack

Attempt caller-supplied fake approval evidence.

Show:

`HTTP 403`

Message:
"SafetyGate accepts only persisted operator approval evidence."

## 7. Operator Approval

Approve through the SafetyGate operator workflow.

Show:

`APPROVED`

Retry the same action.

Show:

`ALLOW`

## 8. Audit Evidence

Open the operator audit view.

Show:
- action ID
- agent/version
- passport
- decision
- policy rule
- approval evidence
- timestamp

Message:
"Every governance decision produces durable evidence."

## 9. Material Change

Change a material part of the certified agent configuration.

Show:

`RECERTIFICATION_REQUIRED`

and runtime denial.

Message:
"The old certification cannot silently authorize a changed agent."

## 10. Recertification

Run admission again for the changed version.

Issue a new Safety Passport.

Message:
"Material change creates a new certification boundary."

## Closing

SafetyGate enforces:

Agent Registration
→ Admission
→ Certification
→ KMS-signed Safety Passport
→ Runtime Authorization
→ Human Review when required
→ Execution or Block
→ Audit
→ Material Change Detection
→ Recertification

Final message:

"No consequential action executes without positive SafetyGate authorization evidence."
