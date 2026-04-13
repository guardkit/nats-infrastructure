---
id: TASK-KV-002
title: Create provision-kv.sh with idempotent KV bucket provisioning
task_type: feature
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-KV-001
status: in_review
estimated_minutes: 45
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7B86
  base_branch: main
  started_at: '2026-04-13T22:43:49.835313'
  last_updated: '2026-04-13T22:51:32.937998'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:43:49.835313'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create provision-kv.sh with idempotent KV bucket provisioning

## Description

Create `kv/provision-kv.sh` following the established idempotency pattern from
`streams/provision-streams.sh`. The script reads bucket definitions from
`kv/kv-definitions.json` and applies the check-then-create-or-update pattern.

## Acceptance Criteria

- [ ] `kv/provision-kv.sh` exists and is executable
- [ ] Reads bucket definitions from `kv/kv-definitions.json`
- [ ] Supports `--dry-run` flag for preview without modification
- [ ] Idempotent: safe to run multiple times (checks if bucket exists before creating)
- [ ] Waits for NATS health before provisioning (same pattern as streams)
- [ ] Supports `NATS_URL` and `NATS_CREDS` environment variables
- [ ] Prints summary: created/updated/current/errors counts
- [ ] Prerequisite checks for `jq` and `nats` CLI
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

Mirror the structure of `streams/provision-streams.sh`:
1. Config section (NATS_URL, NATS_CREDS, DRY_RUN)
2. Prerequisite checks (jq, nats CLI)
3. Build common nats CLI flags
4. Wait for NATS health
5. `provision_kv_bucket()` function using `nats kv add` / `nats kv info`
6. Main loop iterating over definitions
7. Summary output

Key `nats kv` CLI commands:
- `nats kv add BUCKET [flags]` — create bucket
- `nats kv info BUCKET` — check if exists
- `nats kv ls` — list all buckets

Flags for `nats kv add`:
- `--ttl DURATION` (e.g. "7d", "1h")
- `--history N`
- `--storage TYPE` (file or memory)
- `--max-value-size SIZE` (e.g. "64K", "256K")
- `--replicas N`
