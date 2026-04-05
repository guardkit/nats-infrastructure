# ADR-002: Account-Based Multi-Tenancy

**Date:** February 2026
**Status:** Accepted (inherited from Dev Pipeline System Spec ADR-SP-007)

## Context

Multiple projects (internal Appmilla, FinProxy client, GCSE tutor) share the same
NATS server. Client collaborators (e.g., Mark on FinProxy) must be isolated to their
project's topics. Rich and James need full visibility as Appmilla principals.

## Decision

NATS accounts with scoped permissions per project:
- APPMILLA account: Rich + James — full access to all topics
- FINPROXY account: Mark — scoped to `finproxy.>` only
- Topic prefix `{project}.` provides namespace isolation
- SYS account for NATS administration

## Consequences

- Actual security isolation (not just convention)
- Client teams cannot accidentally or maliciously access other projects
- Credential rotation per project
- More NATS configuration per new client project
- Account management overhead scales with client count (acceptable at current scale)
