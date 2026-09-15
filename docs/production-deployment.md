# SafetyGate Production Deployment

## Status

- Project: safetygate-atoosa-2026
- Region: us-west1
- Cloud Run service: safetygate-prod
- Authentication: private Cloud Run IAM
- Public unauthenticated access: disabled

## Production Architecture

Authenticated Client
  -> Cloud Run: safetygate-prod
     -> SafetyGate container on port 8080
     -> OPA sidecar on localhost:8181
     -> Cloud SQL PostgreSQL
     -> Secret Manager
     -> Cloud KMS

## Containers

### SafetyGate

Image:
us-west1-docker.pkg.dev/safetygate-atoosa-2026/safetygate-prod/safetygate@sha256:96e99b3aa2b1b077aac09921b34b4dd97b32efd2b5b30605b2334f2f4a831773

Runs as a non-root user and serves FastAPI with Uvicorn on port 8080.

### OPA

Image:
us-west1-docker.pkg.dev/safetygate-atoosa-2026/safetygate-prod/safetygate-opa@sha256:ea951bd539981ed48b2d6aff34b9637de039cafef54d901973a447de17b00225

OPA listens on port 8181.
SAFETYGATE_OPA_URL=http://127.0.0.1:8181
Cloud Run starts SafetyGate after the OPA startup dependency is satisfied.

## Runtime Identity

Service account:
safetygate-runtime@safetygate-atoosa-2026.iam.gserviceaccount.com

Required production access:
- Cloud SQL Client
- Secret Manager access to safetygate-database-url
- KMS signer/verifier access to the Safety Passport signing key

No user-managed service-account keys are required.

## Database

- Instance: safetygate-prod-db
- Region: us-west1
- PostgreSQL: 16
- Database: safetygate
- Application user: safetygate_app
- Backups: enabled
- Point-in-time recovery: enabled
- Deletion protection: enabled

Secret: safetygate-database-url
Alembic revision: b8d2e4f6a7c9

## Safety Passport Signing

KMS key version:
projects/safetygate-atoosa-2026/locations/global/keyRings/safetygate-dev/cryptoKeys/safety-passport-signing/cryptoKeyVersions/1

The production runtime service account has signer/verifier permission on the Safety Passport signing key.

## Cloud Run Security

Verified controls:
- no allUsers IAM binding
- no allAuthenticatedUsers IAM binding
- unauthenticated requests return 401 or 403
- authenticated /health returns HTTP 200
- dedicated runtime service identity
- immutable application and OPA image digests
- Cloud SQL attached explicitly
- DATABASE_URL injected from Secret Manager
- OPA runs as a sidecar dependency

## Production Verification

Verified:
- production database is at the expected Alembic head
- production runtime identity can sign with KMS
- OPA sidecar runs in the deployed Cloud Run revision
- production runtime identity can connect to Cloud SQL using Secret Manager
- authenticated Cloud Run health check succeeds

## Adversarial and Fail-Closed Proofs

Verified:
- unsigned Safety Passport -> NON_OVERRIDABLE_DENY
- unavailable OPA -> NON_OVERRIDABLE_DENY
- OPA can make an otherwise-authorizable action more restrictive
- configuration change -> recertification required -> hard deny
- tool swap / permission escalation -> hard deny
- tampered KMS Safety Passport signature -> hard deny
- Python terminal hard denies short-circuit OPA

## Deployment Manifest

Production Cloud Run definition:
deploy/cloud-run-service.yaml

The manifest references immutable SafetyGate and OPA image digests.

## Current Validation

- pytest: 172 passed
- known Starlette deprecation warning: backlog, non-blocking
- existing unrelated repo-wide Ruff findings: backlog, not a Step 12 blocker

## Operational Rule

No consequential action may execute without positive SafetyGate authorization evidence.

Enforcement path:
Agent -> Action Proposal -> Python hard gates -> OPA/Rego -> restrictive merge -> authorization -> tool execution -> verification -> audit
