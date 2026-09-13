# SafetyGate Memory Governance

## Purpose

SafetyGate treats agent memory as a governed resource, not as unrestricted model context.

Memory access must satisfy deterministic rules for scope, retention, update behavior, isolation, and permitted memory types before an agent may use or modify stored memory.

## Memory Lifecycle

1. **Memory is created**
   - Memory is associated with an authorized user and agent.
   - Its memory type must be permitted by policy.

2. **Memory is stored**
   - The governing policy defines its scope:
     - SESSION
     - AGENT
     - USER
     - ORGANIZATION

3. **Memory is accessed**
   - SafetyGate checks:
     - requesting agent identity
     - requesting user identity
     - memory owner
     - memory type
     - memory age
     - requested operation

4. **Memory is updated**
   - READ_ONLY permits reads only.
   - APPEND_ONLY permits new entries but prevents normal update/delete operations.
   - CONTROLLED_UPDATE permits policy-authorized modification.

5. **Memory expires**
   - Memory older than the configured retention period is denied access.
   - Expired memory must not silently remain usable by the agent.

## Isolation

When user isolation is enabled, memory belonging to one user cannot be accessed by another user.

When agent isolation is enabled, memory belonging to one agent cannot be accessed by another agent.

Cross-user or cross-agent isolation violations produce:

`NON_OVERRIDABLE_DENY`

They cannot be bypassed by model reasoning, prompt wording, or human approval.

## Contamination Risk

A representative contamination risk is:

> Agent A retrieves memory belonging to User B and uses that information while responding to User A.

This can cause privacy leakage, incorrect personalization, unsafe decisions, or propagation of another user's context.

SafetyGate prevents this by comparing the requesting user and agent identities with the identities bound to the memory before access is authorized.

Example:

User A requests memory owned by User B:

`user-001 -> user-002`

Result:

`NON_OVERRIDABLE_DENY`

## Memory Type Controls

Policies may define:

- allowlisted memory types
- prohibited memory types

Examples of permitted memory might include:

- preference
- task_context

Examples of prohibited memory might include:

- credential
- secret

Explicitly prohibited or non-allowlisted memory types fail closed.

## Security Principle

**Memory retrieval does not equal memory authorization.**

An agent finding or receiving a reference to memory does not establish permission to access it.

Authorization remains controlled by SafetyGate's deterministic governance layer.

## Current Test Evidence

The automated test suite verifies:

- valid memory access
- cross-user isolation
- cross-agent isolation
- retention enforcement
- prohibited memory types
- allowlisted memory types
- read-only restrictions
- append-only restrictions

