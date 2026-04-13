---
id: TASK-KV-003
title: Update setup-gb10.sh to call KV provisioning
task_type: feature
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 2
implementation_mode: direct
complexity: 2
dependencies:
- TASK-KV-002
status: in_review
estimated_minutes: 15
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7B86
  base_branch: main
  started_at: '2026-04-13T22:51:32.961071'
  last_updated: '2026-04-13T22:57:39.686358'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:51:32.961071'
    player_summary: 'Created scripts/setup-gb10.sh as a GB10-specific one-shot deployment
      script following the pattern of the existing scripts/setup.sh. The script has
      an 8-step sequence: (1) prerequisites, (2) NATS CLI install, (3) env file, (4)
      docker compose up, (5) health wait, (6) stream provisioning, (7) KV bucket provisioning,
      (8) verification including nats kv ls. KV provisioning (step 7) is called after
      stream provisioning (step 6) and only after NATS health is confirmed (step 5).
      The script exits non-zero '
    player_success: true
    coach_success: true
---

# Task: Update setup-gb10.sh to call KV provisioning

## Description

Update `scripts/setup-gb10.sh` (or the equivalent one-shot deployment script)
to call `kv/provision-kv.sh` after stream provisioning completes.

The setup sequence should be:
1. Start NATS via Docker Compose
2. Wait for health
3. Provision JetStream streams (`streams/provision-streams.sh`)
4. **Provision KV buckets (`kv/provision-kv.sh`)** <-- NEW
5. Verify

## Acceptance Criteria

- [ ] `scripts/setup-gb10.sh` calls `kv/provision-kv.sh` after stream provisioning
- [ ] KV provisioning runs only after NATS is healthy
- [ ] Script exits non-zero if KV provisioning fails fatally
- [ ] Verification step includes `nats kv ls` to confirm buckets exist
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

The setup script already has the pattern for calling provision-streams.sh.
Add the KV call in the same section, right after stream provisioning.

Also update `scripts/health-check.sh` to include KV bucket listing in its output.
