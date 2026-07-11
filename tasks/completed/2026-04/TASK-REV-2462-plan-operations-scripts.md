---
id: TASK-REV-2462
title: "Plan: Operations Scripts - setup-gb10.sh, health-check.sh, backup-jetstream.sh"
status: completed
task_type: review
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
priority: high
tags: [operations, scripts, gb10, health-check, backup, jetstream]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Already `status: completed` but filed under `backlog/` (status_location_conflict). Feature **FEAT-A4E7** is `status: completed`; deliverables shipped on `main` (pointer commit `n/a — review-task; deliverables present on `main``). No code changed by this sweep.

# Task: Plan Operations Scripts

## Description

Review and plan the implementation of three operational shell scripts for the NATS infrastructure:

1. **setup-gb10.sh** - One-shot setup script for deploying NATS on a fresh Dell DGX Spark GB10
2. **health-check.sh** - Quick health verification script for NATS server, JetStream streams, and connected clients
3. **backup-jetstream.sh** - Backup JetStream data to Synology NAS via rsync

These scripts support Feature 5 (Operations Scripts) from the nats-infrastructure system specification.

## Context

- Target deployment: Dell DGX Spark GB10 (128GB) running DGX OS (Ubuntu 24.04)
- NATS accessible via Tailscale mesh VPN
- Backup target: Synology NAS (optional)
- Scripts location: `scripts/` directory

## Acceptance Criteria

- [ ] Technical options analyzed for each script
- [ ] Error handling and idempotency patterns evaluated
- [ ] Security considerations documented (credentials, network access)
- [ ] Dependencies identified (nats CLI, docker, rsync, jq, curl)
- [ ] Recommended implementation approach selected

## Implementation Notes

Reference: docs/design/specs/nats-infrastructure-system-spec.md (Feature 5)
