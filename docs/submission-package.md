# SafetyGate Submission Package

## Project

**SafetyGate — Independent Certification and Runtime Governance for AI Agents**

## One-Line Description

SafetyGate independently certifies AI agents and prevents consequential actions from executing without valid, policy-compliant authorization evidence.

## Problem

AI agents increasingly act across tools, data, infrastructure, and business systems.

The problem is not simply whether an agent can perform an action.

The problem is whether the exact agent, exact version, exact configuration, requested tool, permissions, risk level, policy context, and required human authority have all been verified before execution.

Without an independent control layer, an agent can potentially operate outside intended boundaries or continue operating after material configuration changes.

## Solution

SafetyGate provides an independent governance layer between an AI agent and consequential execution.

SafetyGate performs:

- agent registration and versioning
- admission evaluation
- certification
- cryptographically signed Safety Passports
- runtime authorization
- Python hard safety gates
- OPA/Rego policy evaluation
- human-review enforcement
- durable audit evidence
- material-change detection
- recertification enforcement

## Certification Model

SafetyGate certification is bound to an exact agent version and configuration.

Certification flow:

Agent Registration
→ Admission
→ PASS
→ KMS-signed Safety Passport
→ ACTIVE certified agent/version

The Safety Passport contains certification evidence including the certified configuration hash, policy version, tool boundaries, and authorized human approvers.

If the agent configuration materially changes, the previous certification cannot silently authorize the changed agent.

SafetyGate requires:

`RECERTIFICATION_REQUIRED`

and runtime operation remains blocked until recertification succeeds.

## Runtime Governance

For every consequential action SafetyGate evaluates:

- agent identity
- certified agent version
- Safety Passport validity
- cryptographic signature
- configuration integrity
- requested tool
- requested permissions
- risk level
- human approval requirements
- Python terminal safety gates
- OPA/Rego policy restrictions

Possible decisions include:

- `ALLOW`
- `ALLOW_WITH_CONDITIONS`
- `HUMAN_REVIEW_REQUIRED`
- `DENY`
- `NON_OVERRIDABLE_DENY`

OPA may make a decision more restrictive, never less restrictive.

## Human Authority

SafetyGate does not allow an agent or API caller to manufacture its own human approval.

Production verification demonstrated:

- forged/self-asserted approval → `HTTP 403`
- high-risk irreversible action without approval → `HUMAN_REVIEW_REQUIRED`
- persisted authorized operator approval → action may be reconsidered
- approved action retry → `ALLOW`

## Fail-Closed Design

SafetyGate fails closed for governance-critical failures.

Verified examples include:

- invalid Safety Passport signature → `NON_OVERRIDABLE_DENY`
- unavailable OPA → `NON_OVERRIDABLE_DENY`
- prohibited tool → deny
- permission escalation → deny
- configuration mismatch → recertification required
- forged approval → `HTTP 403`

## Production Architecture

Production deployment uses:

- Google Cloud Run
- Google Cloud SQL PostgreSQL
- Google Cloud KMS
- Google Secret Manager
- OPA/Rego sidecar
- FastAPI
- immutable container image digests

Production access is protected by private Cloud Run IAM.

Current production SafetyGate image:

`sha256:2d110db4a2d3d7b9c53c98e6e540cda2cd91a28fd8d3cb0d5cc8002b918851fc`

## Demonstrated End-to-End Flow

1. Register agent.
2. Evaluate admission.
3. Receive PASS.
4. Issue KMS-signed Safety Passport.
5. Activate certified agent/version.
6. Submit runtime action.
7. Evaluate Python hard gates.
8. Evaluate OPA/Rego policy.
9. Return authorization decision.
10. Require human review where necessary.
11. Persist authorized operator approval.
12. Re-evaluate approved action.
13. Persist audit evidence.
14. Detect material configuration change.
15. Require recertification before changed agent may operate.

## Security Proof

A production test attempted to submit forged human approval evidence.

SafetyGate returned:

`HTTP 403`

with:

`Valid persisted operator approval evidence was not found.`

A legitimate operator approval was then persisted for a fresh high-risk action.

The same action was retried and returned:

`ALLOW`

## Validation

- automated test suite: `173 passed`
- production deployment verified
- immutable production image verified
- GitHub CI verified
- production KMS signing verified
- production runtime Safety Passport verification verified
- production OPA/Rego decision path verified
- production human-review flow verified
- production forged-approval rejection verified

## Core Principle

**No consequential action executes without positive SafetyGate authorization evidence.**

## Repository

GitHub:

`https://github.com/atoosabiglari-PM/safetygate`

## Demo

Demo script:

`docs/demo-script.md`

Evidence package:

`docs/mvp-closure-evidence.md`

Production deployment evidence:

`docs/production-deployment.md`

## Submission Status

Technical MVP: complete.

Private production MVP deployment: complete and protected by Cloud Run IAM.

Public competition showcase: deployed as an isolated disposable sandbox using a separate service account, dedicated KMS signing key, and ephemeral SQLite storage. It is not customer production.

Commercial and enterprise hardening remains, including application-level identity-provider binding, cryptographic binding of operator identity, monitoring and incident response, tamper-evident audit controls, automated production smoke testing, release-path migration automation, and PostgreSQL-specific concurrency validation.

Evidence and demo package: in final preparation.

Actual competition submission: not yet confirmed.

SafetyGate must not be marked:

`SafetyGate MVP COMPLETE + SUBMITTED`

until the actual submission is confirmed.
