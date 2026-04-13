---
id: TASK-DCD-005
title: Update README with deployment instructions and volume management
task_type: documentation
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 2
implementation_mode: direct
complexity: 1
dependencies:
- TASK-DCD-001
- TASK-DCD-002
status: in_review
priority: normal
tags:
- documentation
- docker
- deployment
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-B464
  base_branch: main
  started_at: '2026-04-13T20:26:50.987944'
  last_updated: '2026-04-13T20:31:21.943984'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T20:26:50.987944'
    player_summary: Updated README.md to replace the pre-implementation Quick Start
      (which referenced non-existent scripts like setup-gb10.sh, provision-streams.sh,
      health-check.sh) with actual docker compose commands reflecting the implemented
      docker-compose.yml and Dockerfile. Added comprehensive Volume Management section
      with backup/restore/reset procedures, health check verification commands for
      all monitoring endpoints, a prominent WARNING about docker compose down -v data
      loss, and Dockerfile/build context do
    player_success: true
    coach_success: true
---

# Task: Update README with Deployment Instructions

## Description

Update the existing `README.md` to reflect the actual Docker Compose deployment now that `docker-compose.yml` and `Dockerfile` exist. The current README references these files but the Quick Start section needs updating to match the actual implementation.

Key updates:
- Quick Start commands updated for `docker compose up -d --build`
- Volume management section added (backup, restore, reset)
- Health check verification commands
- Warning about `docker compose down -v` destroying JetStream data
- Dockerfile build context explanation

## Acceptance Criteria

- [ ] Quick Start section reflects actual `docker compose` commands
- [ ] Volume management section documents backup/restore/reset
- [ ] Health check verification commands included
- [ ] Clear WARNING about `docker compose down -v` data loss
- [ ] Dockerfile and build context documented
