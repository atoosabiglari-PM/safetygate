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
11. Atomic durable execution claim
12. Idempotency and duplicate suppression
13. Execution, retry, fallback, or escalation
14. Durable execution outcome recording
15. Persistent audit evidence

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

The current prototype trusts caller-provided principal identity. Production deployment requires integration with a trusted identity provider.

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

High-risk irreversible actions require human approval where policy permits.

Approval validation includes:

- action identity match
- authorized approver identity
- explicit approval result

Approval evidence is persisted independently from the runtime audit record.

Reuse of an approval identifier with different approval evidence is rejected.

Prompt wording cannot convert a hard deny into an approval.

Approval satisfies only risks that policy explicitly permits humans to approve.

## Governed Tool Execution

Tool execution is schema validated before invocation.

Malformed tool arguments fail closed before execution.

The execution boundary verifies that the requested `action_id` and `tool_name` exactly match the previously authorized proposal.

This prevents an authorized action from being swapped for a different tool immediately before execution.

## Durable Idempotency and Duplicate Protection

When database persistence is enabled, SafetyGate creates an atomic durable execution claim before tool execution.

The idempotency key is uniquely constrained by the database.

A repeated idempotency key with the same action fingerprint is suppressed.

A reused idempotency key with a different action payload fails closed.

Concurrent callers racing for the same execution cannot both acquire the durable claim.

The automated concurrency test deliberately starts two callers simultaneously and verifies that the underlying executor runs exactly once.

## Durable Execution States

Execution records use explicit durable states:

- `PENDING`
- `EXECUTED`
- `FALLBACK_EXECUTED`
- `FAILED_CLOSED`
- `HUMAN_REVIEW_REQUIRED`
- `UNCERTAIN`

Terminal workflow paths persist their execution result instead of leaving a claimed action indefinitely in `PENDING`.

Each execution record includes creation and update timestamps to support recovery reasoning.

## Crash Recovery and Uncertain Outcomes

A process can fail after obtaining an execution claim but before SafetyGate receives or persists a final tool result.

For consequential external actions, absence of a response does not prove that the action did not happen.

SafetyGate therefore does not blindly retry stale `PENDING` actions.

When a `PENDING` execution exceeds the configured recovery window, it transitions to:

`UNCERTAIN`

`UNCERTAIN` means SafetyGate cannot prove whether the external side effect occurred.

A subsequent request for that execution receives the uncertain result rather than automatically executing the tool again.

This behavior is intended to prevent duplicate real-world actions when execution outcome is ambiguous.

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
- completed duplicate actions are suppressed
- stale ambiguous execution claims become `UNCERTAIN`

Automatic fallback is restricted to explicitly designated safe fallback tools.

Fallback does not bypass authorization.

## Persistent Audit Evidence

Runtime audit evidence can be persisted through the governed workflow.

Persistent audit entries capture governance evidence including:

- event and timestamp
- action identity
- agent and version identity
- Safety Passport identity and status
- tool and action
- requested permissions
- certified and current configuration hashes
- approval identity and outcome where applicable
- principal identity and roles
- enforcement reasons
- runtime decision
- reasons and conditions
- evidence
- execution outcome

Approval evidence is also stored persistently and is bound to the approved action and approver identity.

Runtime audit event identifiers and approval identifiers are uniquely constrained to protect evidence integrity.

## Secret-Safe Logging

Audit evidence is recursively sanitized before persistence.

Known sensitive fields such as API keys, authorization headers, access tokens, refresh tokens, passwords, client secrets, private keys, and related secret fields are replaced with:

`[REDACTED]`

Non-sensitive governance context is preserved so evidence remains useful for review and incident analysis.

Redaction tests verify that original secret values do not appear in serialized audit output.

## Memory Governance

Memory governance is documented separately in:

`docs/memory-governance.md`

Memory retrieval does not equal memory authorization.

Memory controls include scope, retention, update policy, type allowlists and prohibitions, user isolation, and agent isolation.

## Current Scope

The current implementation is a deterministic governance kernel with persistent runtime evidence, durable execution claims, failure handling, crash-recovery controls, and concurrency protection.

It should not yet be described as a complete production runtime control plane.

The default tool executor remains simulated. Production deployment still requires real authenticated identity, production tool or MCP adapters, and infrastructure hardening.

Planned production capabilities include:

- trusted identity-provider integration
- formal policy provenance and rule hierarchy
- cryptographically signed Safety Passports
- external policy-engine integration
- real MCP and production tool adapters
- production database and cloud deployment
- operator-facing API and user interface

## Validation

The automated test suite exercises allowed, denied, failure, recovery, and adversarial paths including:

- admission controls
- Safety Passport validation
- permission enforcement
- human approval
- persistent approval evidence
- role enforcement
- memory isolation
- tool schema validation
- authorization/execution binding
- conditional authorization
- durable duplicate suppression
- process-restart persistence
- simultaneous concurrency
- retry behavior
- safe fallback
- partial-failure escalation
- stale `PENDING` recovery to `UNCERTAIN`
- persistent runtime audit evidence
- secret redaction
- prompt-based authorization bypass attempts

Run `pytest -q` to execute the test suite.

SafetyGate is designed so that governance decisions can be inspected and tested independently of the underlying AI model.
