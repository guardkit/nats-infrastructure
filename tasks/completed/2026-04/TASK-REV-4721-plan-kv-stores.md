---
id: TASK-REV-4721
title: "Plan: KV Stores - agent-status, agent-registry, pipeline-state, jarvis-session buckets"
status: completed
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 3
  recommendations_count: 1
  decision: implement
  approach: "Option 1 - Separate KV Script + Definitions"
  feature_id: FEAT-7B86
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
priority: high
tags: [kv-store, jetstream, infrastructure, nats]
task_type: review
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Already `status: completed` but filed under `backlog/` (status_location_conflict). Feature **FEAT-7B86** is `status: completed`; deliverables shipped on `main` (pointer commit `6af7348`). No code changed by this sweep.

# Task: Plan KV Stores - agent-status, agent-registry, pipeline-state, jarvis-session buckets

## Description

Plan the implementation of NATS JetStream KV bucket provisioning for four buckets
used by the agent fleet:

- **agent-status**: Last known status per agent (persistent, no TTL)
- **agent-registry**: Fleet routing table - agent capability manifests (persistent, no TTL)
- **pipeline-state**: Current pipeline state per feature_id (7-day TTL)
- **jarvis-session**: Jarvis conversation session context (1-hour TTL)

This is Feature 6 from the nats-infrastructure system spec. The work involves:
- Adding KV bucket creation to provision-streams.sh
- Documenting KV usage patterns (get/put/watch)
- Testing KV watch for agent status and registry changes

## Context

- System spec: docs/design/specs/nats-infrastructure-system-spec.md (Feature 6)
- Multi-tenancy: docs/design/decisions/ADR-002-account-multi-tenancy.md
- KV buckets serve the APPMILLA account (fleet-wide agent state)
- Deployed on Dell DGX Spark GB10

## Acceptance Criteria

- [ ] Technical options analysed for KV provisioning approach
- [ ] Bucket configuration (TTL, max size, history) recommended
- [ ] Account scoping implications assessed
- [ ] Implementation tasks defined with dependencies

## Implementation Notes

Review task - analysis only, no implementation.
