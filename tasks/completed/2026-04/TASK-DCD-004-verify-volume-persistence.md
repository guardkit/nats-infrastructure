---
id: TASK-DCD-004
title: Verify volume persistence - JetStream data survives container restart
task_type: testing
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 2
implementation_mode: direct
complexity: 2
dependencies:
- TASK-DCD-001
- TASK-DCD-002
status: completed
priority: high
tags:
- docker
- nats
- jetstream
- testing
- persistence
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-B464
  base_branch: main
  started_at: '2026-04-13T20:26:50.990937'
  last_updated: '2026-04-13T20:32:14.931133'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T20:26:50.990937'
    player_summary: Created comprehensive test file (test_volume_persistence.py) with
      21 configuration-level tests organized into 5 test classes mapping 1:1 to the
      5 acceptance criteria, plus 4 integration tests gated behind @pytest.mark.integration
      for live Docker testing. Added data loss warning about `docker compose down
      -v` to docker-compose.yml header and volumes section. README.md already contained
      thorough volume management documentation including the data loss warning.
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-B464** is `status: completed`; deliverables shipped on `main` (pointer commit `bda0704`). No code changed by this sweep.

# Task: Verify Volume Persistence

## Description

Verify that JetStream data persists across container restarts by:
1. Starting NATS via `docker compose up -d`
2. Creating a test stream and publishing messages
3. Stopping with `docker compose down` (NOT `-v`)
4. Starting again with `docker compose up -d`
5. Verifying the test stream and messages still exist

This confirms the named volume `nats-data` correctly persists `/data/jetstream`.

## Context

- Named volume `nats-data` maps to `/data/jetstream` inside the container
- `docker compose down` preserves named volumes; `docker compose down -v` destroys them
- JetStream uses file-based storage (`store_dir: /data/jetstream`)
- Requires `nats` CLI tool for stream creation and message publishing

## Acceptance Criteria

- [ ] Test stream created and messages published successfully
- [ ] After `docker compose down` + `up`, stream still exists
- [ ] After `docker compose down` + `up`, published messages still retrievable
- [ ] Volume listed in `docker volume ls` as `nats-infrastructure_nats-data`
- [ ] Documented: `docker compose down -v` WARNING about data loss

## Verification Commands

```bash
# Start and create test data
docker compose up -d --build
sleep 3

# Create test stream (requires nats CLI)
nats stream add TEST-PERSISTENCE \
    --subjects "test.persistence.>" \
    --retention limits \
    --max-msgs 100 \
    --storage file \
    --replicas 1 \
    --defaults

# Publish test message
nats pub test.persistence.check "hello-persistence-$(date +%s)"

# Verify message count
nats stream info TEST-PERSISTENCE

# Restart
docker compose down
docker compose up -d
sleep 3

# Verify stream survived
nats stream info TEST-PERSISTENCE
# Should show same message count

# Cleanup
nats stream rm TEST-PERSISTENCE -f
docker compose down
```
