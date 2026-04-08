---
id: TASK-NATS-004
title: Create verification script for NATS startup and JetStream
status: in_review
task_type: testing
parent_review: TASK-REV-69BD
feature_id: FEAT-NATS-CFG
wave: 4
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-NATS-001
- TASK-NATS-002
- TASK-NATS-003
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-D2AD
  base_branch: main
  started_at: '2026-04-08T09:56:27.920430'
  last_updated: '2026-04-08T10:04:53.463763'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T09:56:27.920430'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Create Verification Script for NATS Startup and JetStream

## Description

Create a verification script (`scripts/verify-nats.sh`) that confirms NATS server starts correctly with the configuration from TASK-NATS-001 through TASK-NATS-003. The script should validate JetStream initialisation, monitoring endpoint availability, and basic account authentication.

## Requirements

The verification script must check:

1. **NATS server starts** — process is running, port 4222 accepting connections
2. **JetStream initialised** — `/jsz` endpoint returns JetStream info
3. **Monitoring endpoint responds** — `http://localhost:8222/healthz` returns 200
4. **Server info correct** — server_name is `ships-computer`, version reported
5. **Account authentication works** — APPMILLA user can connect, FINPROXY user can connect with scoped access

## Acceptance Criteria

- [ ] `scripts/verify-nats.sh` exists and is executable
- [ ] Script checks NATS server is healthy via port 8222 healthcheck
- [ ] Script verifies JetStream is enabled via `/jsz` endpoint
- [ ] Script verifies server_name is `ships-computer` via `/varz` endpoint
- [ ] Script reports clear PASS/FAIL for each check
- [ ] Script exits with non-zero code if any check fails
- [ ] Script works both locally and in CI (uses curl, not nats CLI dependency)

## Implementation Notes

- Use `curl` for HTTP checks (available everywhere, no extra dependencies)
- Use `jq` for JSON parsing if available, fallback to grep if not
- Health endpoint: `http://localhost:8222/healthz`
- Server info: `http://localhost:8222/varz`
- JetStream info: `http://localhost:8222/jsz`
- Account auth testing requires `nats` CLI or raw TCP — keep this optional with a clear skip message if `nats` CLI not installed
- Script should timeout after 30 seconds if NATS hasn't started
