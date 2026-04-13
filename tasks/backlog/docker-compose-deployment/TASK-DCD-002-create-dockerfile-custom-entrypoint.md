---
id: TASK-DCD-002
title: Create Dockerfile for custom entrypoint with envsubst support
task_type: scaffolding
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
status: in_review
priority: high
tags:
- docker
- nats
- infrastructure
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-B464
  base_branch: main
  started_at: '2026-04-13T20:19:45.272749'
  last_updated: '2026-04-13T20:26:21.334776'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T20:19:45.272749'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create Dockerfile for Custom Entrypoint

## Description

Create a thin `Dockerfile` that extends the official NATS Alpine image to guarantee `envsubst` (from `gettext`) is available, and copies the entrypoint script into the image. This makes the deployment self-contained — no dependency on host-mounted scripts at runtime.

```dockerfile
FROM nats:2.11-alpine
RUN apk add --no-cache gettext
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["-c", "/etc/nats/nats-server.conf"]
```

## Context

- Entrypoint: `scripts/docker-entrypoint.sh` uses `envsubst` to process account templates
- `envsubst` comes from the `gettext` package — may or may not be in the base NATS Alpine image
- The Dockerfile guarantees the dependency and makes the setup portable
- `docker-compose.yml` (TASK-DCD-001) should use `build: .` instead of `image:` when Dockerfile exists

## Acceptance Criteria

- [ ] `Dockerfile` exists at repo root
- [ ] Extends `nats:2.11-alpine`
- [ ] Installs `gettext` package (provides `envsubst`)
- [ ] Copies `docker-entrypoint.sh` into image
- [ ] Sets entrypoint and default CMD
- [ ] `.dockerignore` created to exclude `.git`, `docs/`, `tasks/`, `.claude/`, `.guardkit/`
- [ ] `docker-compose.yml` updated to use `build: .` context
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

Update TASK-DCD-001's docker-compose.yml to use `build: .` instead of `image: nats:2.11-alpine` when both tasks are implemented. The two tasks can run in parallel since this is a known coordination point.
