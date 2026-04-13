---
complexity: 3
dependencies: []
feature_id: FEAT-DCD
id: TASK-DCD-002
implementation_mode: task-work
parent_review: TASK-REV-1A6B
priority: high
status: design_approved
tags:
- docker
- nats
- infrastructure
task_type: scaffolding
title: Create Dockerfile for custom entrypoint with envsubst support
wave: 1
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