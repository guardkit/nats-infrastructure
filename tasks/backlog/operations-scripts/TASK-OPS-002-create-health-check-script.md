---
id: TASK-OPS-002
title: "Create health-check.sh monitoring probe"
task_type: scaffolding
parent_review: TASK-REV-2462
feature_id: FEAT-OPS
status: pending
priority: high
complexity: 2
wave: 1
implementation_mode: direct
dependencies: []
tags: [operations, health-check, monitoring]
---

# Task: Create health-check.sh Monitoring Probe

## Description

Create a lightweight, curl-based health check script for quick operational verification of the NATS server. This script queries NATS monitoring endpoints to report server status, JetStream usage, stream count, and connected clients.

## Context

- Distinct from `verify-nats.sh` which is a post-deploy configuration verification
- `health-check.sh` is an operational probe: "is it up and how is it doing?"
- Designed to be called by cron, monitoring tools, or manual spot checks
- NATS monitoring HTTP API is unauthenticated (port 8222)

## Reference

- System spec: `docs/design/specs/nats-infrastructure-system-spec.md` (Feature 5)
- Existing pattern: `scripts/verify-nats.sh` for helper functions and output style

## Acceptance Criteria

- [ ] Script queries `/varz` for server name, version, and uptime
- [ ] Script queries `/jsz` for JetStream memory and storage usage
- [ ] Script queries `/connz` for connected client count
- [ ] Script reports stream count (from `/jsz` streams field)
- [ ] Exit code 0 = healthy, 1 = degraded (partial failure), 2 = unreachable
- [ ] Monitoring URL configurable via `NATS_MONITOR_URL` env var (default: `http://localhost:8222`)
- [ ] Uses `curl` (required) and `jq` (optional, with grep fallback)
- [ ] Script uses `set -euo pipefail` and `#!/bin/bash`
- [ ] Script is executable (`chmod +x`)

## Implementation Notes

Keep the output human-readable by default. Follow the `verify-nats.sh` helper pattern for `jq`/grep fallback JSON parsing.
