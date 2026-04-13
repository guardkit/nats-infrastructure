---
id: TASK-DCD-005
title: "Update README with deployment instructions and volume management"
task_type: documentation
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 2
implementation_mode: direct
complexity: 1
dependencies:
  - TASK-DCD-001
  - TASK-DCD-002
status: pending
priority: normal
tags: [documentation, docker, deployment]
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
