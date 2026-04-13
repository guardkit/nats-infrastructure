---
id: TASK-OPS-004
title: "Test operations scripts against running NATS"
task_type: testing
parent_review: TASK-REV-2462
feature_id: FEAT-OPS
status: pending
priority: high
complexity: 3
wave: 2
implementation_mode: direct
dependencies:
  - TASK-OPS-001
  - TASK-OPS-002
  - TASK-OPS-003
tags: [operations, testing, integration]
---

# Task: Test Operations Scripts Against Running NATS

## Description

Verify all three operations scripts work correctly against a running Docker Compose NATS environment. This includes end-to-end testing of setup, health checking, and backup (where NAS is available).

## Context

- Docker Compose NATS is already defined and working
- Scripts should be tested in the order: setup-gb10.sh, health-check.sh, backup-jetstream.sh
- NAS backup testing may need to be mocked if NAS is not available in test environment

## Reference

- Parent tasks: TASK-OPS-001, TASK-OPS-002, TASK-OPS-003
- Existing test pattern: `scripts/verify-nats.sh` (can be used as integration test baseline)

## Acceptance Criteria

- [ ] `setup-gb10.sh` runs successfully on a clean Docker environment (after `docker compose down`)
- [ ] `setup-gb10.sh` is idempotent — running twice produces no errors
- [ ] `health-check.sh` returns exit code 0 when NATS is running and healthy
- [ ] `health-check.sh` returns exit code 2 when NATS is not running
- [ ] `health-check.sh` output includes server name, version, JetStream status, and client count
- [ ] `backup-jetstream.sh` handles unreachable NAS gracefully (exit code 2, clear error message)
- [ ] `backup-jetstream.sh` pre-flight check works (SSH connectivity test)
- [ ] All scripts have correct shebang (`#!/bin/bash`) and are executable
- [ ] All scripts fail fast on missing dependencies with clear error messages

## Implementation Notes

Test `health-check.sh` in both healthy and unhealthy states. For `backup-jetstream.sh`, test the NAS-unreachable path since the NAS may not be available in all environments.
