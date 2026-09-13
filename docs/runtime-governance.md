# Runtime Governance

SafetyGate is an independent governance and runtime authorization layer for AI agents.

Its core runtime question is:

> Before an AI agent takes an action, can we prove that the action is authorized, bounded, reviewable, and safe enough to execute?

SafetyGate does not make the underlying model safe. It governs what AI agents are permitted to do in real systems.

## Core Runtime Invariant

> No consequential action executes without positive authorization evidence.

Model reasoning, user instructions, retrieved memory, external content, and tool output are treated as probabilistic or untrusted inputs.

Identity, permissions, role boundaries, Safety Passport state, configuration binding, approval evidence, and deterministic policy remain authoritative.

## Authorization Sequence

The governed runtime path evaluates:

1. Agent admission
2. Safety Passport validity
3. Certified configuration binding
4. Tool allowlist and prohibition boundaries
5. Deterministic permission contract
6. Human approval requirements
7. Conditional authorization requirements
8. Exact authorization-to-execution binding
9. Principal role authorization
10. Tool argument schema validation
11. Idempotency and duplicate suppression
12. Execution, retry, fallback, or escalation
13. Audit outcome recording

Authorization and execution are separate boundaries.

A tool that was not authorized cannot be substituted immediately before execution.

## Identity and Roles

SafetyGate uses explicit principal identity and deterministic runtime roles.

Current roles:

- `READER`
- `OPERATOR`
- `APPROVER`

Current runtime boundaries:

- `READER` may execute approved read operations such as `read_documents`.
- `OPERATOR` may execute approved operational tools including `read_documents`, `send_message`, and `deploy_service`.
- `APPROVER` does not automatically receive tool execution authority.

Human approval and execution authority are intentionally separate concepts.

An authorized approver may approve an action where policy permits, but approval alone does not grant permission to execute a tool.

## Permissions and Tool Contracts

Each registered tool has a deterministic permission requirement.

Examples:

- `read_documents` requires `documents:read`
- `send_message` requires `messages:send`
- `deploy_service` requires `deploy:write`
- `delete_records` requires `records:delete`

Tool discovery does not equal tool authorization.

Unknown tool contracts fail closed.

Missing required permissions fail closed.

## Safety Passport Binding

Runtime authorization requires an active Safety Passport whose certified configuration matches the current configuration.

If the passport is invalid, revoked, or bound to a different material configuration, execution is denied and recertification is required where applicable.

Passport tool boundaries distinguish:

- allowed tools
- conditional tools
- prohibited tools

Human approval cannot override a hard SafetyGate deny.

## Conditional Authorization

SafetyGate supports:

- `ALLOW`
- `ALLOW_WITH_CONDITIONS`
- `HUMAN_REVIEW_REQUIRED`
- `DENY`
- `NON_OVERRIDABLE_DENY`

Current supported runtime conditions include:

- record full audit evidence
- verify execution result

Unsupported conditions fail closed rather than silently degrading into unconditional execution.

If required post-execution verification is not satisfied, the workflow escalates instead of reporting silent success.

## Human Approval

High-risk irreversible actions require verified human approval.

Approval validation includes:

- action identity match
- authorized approver identity
- explicit approval result

Prompt wording cannot convert a hard deny into an approval.

Approval satisfies only risks that policy explicitly permits humans to approve.

## Governed Tool Execution

Tool execution is schema validated before invocation.

Malformed tool arguments fail closed before execution.

The execution boundary also verifies that the requested `action_id` and `tool_name` exactly match the previously authorized proposal.

This prevents an authorized action from being swapped for a different tool immediately before execution.

## Idempotency and Duplicate Protection

SafetyGate currently maintains idempotency records for simulated execution.

A repeated idempotency key with the same action fingerprint is suppressed.

A reused idempotency key with a different payload fails closed.

This prevents accidental duplicate execution in the current runtime demonstration.

### Current limitation

The current idempotency store is in memory.

It demonstrates the governance rule and test behavior but is not yet a durable production-grade idempotency store across process restarts or multiple service instances.

## Failure Handling

Execution failures are classified into:

- timeout
- transient failure
- partial failure
- unknown failure

Current policy:

- retry-safe read operations may retry timeout or transient failures
- consequential operations are not automatically retried when completion status may be unknown
- partial failure requires human review
- unknown failure fails closed
- duplicate completed actions are suppressed

Automatic fallback is restricted to explicitly designated safe fallback tools.

Fallback does not bypass authorization.

## Audit Evidence

Runtime audit records capture governance evidence including:

- event and timestamp
- action identity
- agent and version identity
- Safety Passport identity and status
- tool and action
- requested permissions
- certified and current configuration hashes
- approval identity and outcome where applicable
- runtime decision
- reasons and conditions
- evidence
- execution outcome

Audit evidence is automatically created through the governed runtime authorization path.

## Secret-Safe Logging

Audit evidence is recursively sanitized before storage in the runtime audit record.

Known sensitive fields such as API keys, authorization headers, access tokens, refresh tokens, passwords, client secrets, private keys, and related secret fields are replaced with:

`[REDACTED]`

Non-sensitive governance context is preserved so logs remain useful for review and incident analysis.

Redaction tests verify that original secret values do not appear in serialized audit output.

## Memory Governance

Memory governance is documented separately in:

`docs/memory-governance.md`

Memory retrieval does not equal memory authorization.

Memory controls include scope, retention, update policy, type allowlists and prohibitions, user isolation, and agent isolation.

## Current Scope

The current implementation is a governed, simulated runtime proof suitable for validating SafetyGate's control model.

It demonstrates real deterministic authorization logic and failure controls, but it should not yet be described as a complete production deployment.

Examples of later production hardening include:

- durable distributed idempotency
- persistent audit storage
- production identity-provider integration
- production tool adapters
- cryptographically signed Safety Passports
- policy-engine integration and deployment hardening
- distributed execution coordination

## Validation

The automated test suite exercises allowed and denied paths including:

- admission controls
- Safety Passport validation
- permission enforcement
- human approval
- role enforcement
- memory isolation
- tool schema validation
- authorization/execution binding
- conditional authorization
- duplicate suppression
- retry behavior
- safe fallback
- partial-failure escalation
- audit creation
- secret redaction

Run `pytest -q` to execute the test suite.

SafetyGate is designed so that governance decisions can be inspected and tested independently of the underlying AI model.
