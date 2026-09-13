# SafetyGate

**Independent governance and runtime authorization for AI agents.**

> Before an AI agent takes an action, can we prove that the action is authorized, bounded, reviewable, and safe enough to execute?

SafetyGate is a model-independent governance layer between AI reasoning and real-world execution.

It does not make the underlying model inherently safe. It governs what an AI agent is permitted to do in connected systems.

> **Models can propose. SafetyGate decides.**

## Core Invariant

> **No consequential action executes without positive authorization evidence.**

Execution authority is based on deterministic governance evidence including verified identity, trusted roles, certified configuration, tool permissions, policy, risk, human approval where required, and runtime evidence.

## Implemented Controls

SafetyGate currently includes:

- agent admission
- Safety Passport validation
- material-change recertification
- OIDC/JWT identity verification
- trusted role resolution
- deterministic tool permissions
- human approval boundaries
- authorization-to-execution binding
- policy hierarchy and provenance
- memory governance
- persistent audit evidence
- durable idempotency
- concurrency protection
- retry and fallback controls
- crash recovery
- explicit `UNCERTAIN` execution state

## Policy Hierarchy and Provenance

SafetyGate currently models this authority hierarchy:

1. Mandatory Law
2. Fundamental Rights
3. AI Governance Standards
4. Security Standards
5. Organization Policy
6. Agent Identity & Permissions
7. Human Authority
8. Runtime Evidence

A weaker authority cannot erase a stronger restriction.

## Security Principles

**Identity before autonomy.**

**Governance before deployment.**

**Safety before execution.**

**Tool discovery does not equal tool authorization.**

**Memory retrieval does not equal memory authorization.**

## Current Status

SafetyGate is currently a governance kernel and security architecture prototype.

It should **not yet be described as a complete production control plane**.

The current default tool execution path remains simulated.

Planned production work includes:

- KMS-backed Safety Passport signing
- external OPA/Rego policy integration
- real MCP and production tool adapters
- production identity-provider configuration
- authenticated API boundary
- PostgreSQL / Cloud SQL production validation
- hardened cloud deployment
- Secret Manager integration
- monitoring and incident response
- operator API and UI

## Documentation

- [Runtime Governance](docs/runtime-governance.md)
- [Memory Governance](docs/memory-governance.md)
- [Threat Model](docs/threat-model.md)

## Development

Python 3.11+ is required.

Install the project and development dependencies with `pip install -e '.[dev]'`.

Run the test suite with `pytest -q`.

## What SafetyGate Does Not Claim

SafetyGate does not claim to make an AI model truthful, eliminate hallucinations, make external tools trustworthy, replace identity providers, or replace legal analysis.

SafetyGate governs **execution authority**.

It does not turn probabilistic AI reasoning into deterministic truth.

## License

Apache License 2.0.

> **Models will change. The governance boundary between intelligence and execution should remain independently enforceable.**
