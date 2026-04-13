---
id: TASK-REV-E14C
title: "Plan: JetStream Stream Definitions - PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM streams"
status: backlog
created: 2026-04-13T10:00:00Z
updated: 2026-04-13T10:00:00Z
priority: high
tags: [jetstream, nats, streams, infrastructure]
task_type: review
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan JetStream Stream Definitions

## Description

Analyze and plan the implementation of 6 core JetStream stream definitions (PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM) plus a project-scoped stream template (FINPROXY). This includes creating a declarative stream-definitions.json, an idempotent provision-streams.sh script, and validation tests for stream retention policies.

## Context

- System spec: docs/design/specs/nats-infrastructure-system-spec.md (Feature 3)
- Deployment target: Dell DGX Spark GB10
- NATS server with JetStream enabled (max_mem: 1GB, max_file: 10GB)
- Streams serve the Ship's Computer agent fleet

## Review Focus

- All aspects (comprehensive)
- Trade-off priority: Balanced
- Specific concern: Idempotency of provisioning script

## Acceptance Criteria

- [ ] Technical options analyzed for stream provisioning approach
- [ ] Idempotency strategy for stream creation/updates evaluated
- [ ] Retention policies validated against use cases
- [ ] Implementation tasks defined with clear dependencies
