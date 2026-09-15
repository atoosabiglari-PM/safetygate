# SafetyGate MVP Closure Evidence

## Status

SafetyGate Steps 1–13 are complete and frozen.

Current phase:
MVP Closure — Evidence, Certification Proof, Demo, and Submission Package.

## Production Baseline

- GCP project: `safetygate-atoosa-2026`
- Region: `us-west1`
- Cloud Run service: `safetygate-prod`
- Production access: private Cloud Run IAM
- Production SafetyGate image:

  `sha256:2d110db4a2d3d7b9c53c98e6e540cda2cd91a28fd8d3cb0d5cc8002b918851fc`

- OPA runs as a Cloud Run sidecar.
- PostgreSQL is hosted in Cloud SQL.
- Safety Passport cryptographic signing and verification use Google Cloud KMS.
- Production secrets are supplied through Secret Manager.

## Core Governance Rule

No consequential action may execute without positive SafetyGate authorization evidence.

Runtime path:

Agent
→ Action Proposal
→ SafetyGate Python hard gates
→ OPA/Rego policy evaluation
→ Restrictive decision merge
→ ALLOW / ALLOW_WITH_CONDITIONS / HUMAN_REVIEW_REQUIRED / DENY / NON_OVERRIDABLE_DENY
→ execution or block
→ verification
→ audit

OPA may make a decision more restrictive, never less restrictive.

## Certification Lifecycle Evidence

SafetyGate certification is bound to an exact agent version and configuration.

Lifecycle:

Agent Registration
→ Admission Evaluation
→ PASS
→ KMS-signed Safety Passport
→ ACTIVE certified agent/version
→ runtime authorization
→ material configuration change
→ RECERTIFICATION_REQUIRED
→ runtime hard deny until recertification succeeds

Verified certification properties:

- Safety Passport is issued only after successful admission.
- Passport contains the certified configuration hash.
- Passport signature is generated using Google Cloud KMS.
- Runtime verifies the cryptographic Safety Passport before authorization.
- Runtime compares current configuration with the certified configuration.
- Tampered or invalid passport signature fails closed.
- Material configuration change requires recertification.
- An agent cannot continue operating under certification for a materially changed configuration.

## Human Approval Security Evidence

Production verification confirmed:

1. A high-risk irreversible action without approval returned:

   `HUMAN_REVIEW_REQUIRED`

2. A caller attempted to self-assert a forged approval.

   Production response:

   `HTTP 403`

   Reason:

   `Valid persisted operator approval evidence was not found.`

3. An authorized operator persisted approval evidence for the action.

4. The same action was retried using the persisted approval ID.

   Production decision:

   `ALLOW`

This proves that an agent or caller cannot manufacture its own human authorization evidence.

## Fail-Closed Evidence

Verified SafetyGate failure behavior includes:

- invalid Safety Passport signature → `NON_OVERRIDABLE_DENY`
- unavailable OPA → `NON_OVERRIDABLE_DENY`
- configuration mismatch → recertification required / hard deny
- prohibited tool use → hard deny
- permission escalation → hard deny
- forged human approval → HTTP 403
- Python terminal hard denies cannot be relaxed by OPA

## Production Human Review Proof

Fresh production action:

- risk level: `HIGH`
- irreversible: `true`
- tool: `read_documents`
- requested permission: `documents:read`

Initial result:

`HUMAN_REVIEW_REQUIRED`

After persisted authorized operator approval:

`ALLOW`

The final authorization audit event was persisted in the production audit trail.

## Validation

Current automated validation:

- pytest: `173 passed`
- production deployment verified on immutable image digest
- GitHub CI verified on approval-hardening commits
- known Starlette deprecation warning: non-blocking backlog

## Demo Flow

The submission demo should show this sequence:

1. Register an agent.
2. Show the agent configuration and requested tools/permissions.
3. Run SafetyGate admission.
4. Show PASS.
5. Issue the KMS-signed Safety Passport.
6. Show the certified agent version and configuration hash.
7. Propose a normal runtime action and show authorization.
8. Propose a high-risk irreversible action.
9. Show `HUMAN_REVIEW_REQUIRED`.
10. Attempt forged/self-asserted approval and show rejection.
11. Approve through the SafetyGate operator workflow.
12. Retry the action and show `ALLOW`.
13. Show the audit evidence.
14. Materially change the agent configuration.
15. Show `RECERTIFICATION_REQUIRED` and runtime denial.
16. Recertify before allowing the changed agent to operate again.

## MVP Closure Criterion

SafetyGate may be marked:

`SafetyGate MVP COMPLETE + SUBMITTED`

only after the submission package is complete and the actual competition submission is confirmed.
