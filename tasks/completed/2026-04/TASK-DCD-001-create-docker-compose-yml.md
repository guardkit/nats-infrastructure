---
id: TASK-DCD-001
title: Create docker-compose.yml with NATS service, volume, network, health check
task_type: scaffolding
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
status: completed
priority: high
tags:
- docker
- nats
- jetstream
- infrastructure
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-B464
  base_branch: main
  started_at: '2026-04-13T20:19:45.274307'
  last_updated: '2026-04-13T20:26:50.958823'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T20:19:45.274307'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-B464** is `status: completed`; deliverables shipped on `main` (pointer commit `bda0704`). No code changed by this sweep.

# Task: Create docker-compose.yml

## Description

Create the root `docker-compose.yml` defining the NATS server service with:
- `nats:2.11-alpine` base image
- Custom entrypoint using existing `scripts/docker-entrypoint.sh` for envsubst password injection
- Named volume `nats-data` for JetStream persistence at `/data/jetstream`
- Health check via `wget --spider -q http://localhost:8222/healthz` with `start_period: 5s`
- Restart policy `unless-stopped`
- Ports 4222 (client) and 8222 (monitoring)
- Custom network `ships-computer` for future fleet compose extension
- `env_file: .env` for password variables
- Read-only config mounts (`:ro`)

## Context

- Server config: `config/nats-server.conf` (JetStream store_dir: `/data/jetstream`)
- Account template: `config/accounts/accounts.conf.template` (envsubst placeholders)
- Entrypoint: `scripts/docker-entrypoint.sh` (validates 4 password vars, runs envsubst, execs nats-server)
- Env vars: `.env.example` documents all 4 required password variables
- System spec: `docs/design/specs/nats-infrastructure-system-spec.md` (Feature 4)

## Acceptance Criteria

- [ ] `docker-compose.yml` exists at repo root with NATS service definition
- [ ] Service uses `nats:2.11-alpine` image (pinned major version)
- [ ] Custom entrypoint points to `docker-entrypoint.sh` for envsubst processing
- [ ] Named volume `nats-data` mounted at `/data/jetstream`
- [ ] Health check configured with `start_period`, `interval`, `timeout`, `retries`
- [ ] Restart policy set to `unless-stopped`
- [ ] Ports 4222 and 8222 exposed
- [ ] Custom network `ships-computer` created
- [ ] Config directories mounted read-only
- [ ] `env_file` references `.env`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

The entrypoint script expects config at `/etc/nats/config/accounts/` for templates and outputs processed config to `/etc/nats/accounts/`. The `nats-server.conf` includes `accounts/*.conf` which matches the entrypoint output path. Ensure volume mounts align with these paths.
