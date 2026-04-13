---
id: TASK-OPS-001
title: "Create setup-gb10.sh one-shot deployment script"
task_type: scaffolding
parent_review: TASK-REV-2462
feature_id: FEAT-OPS
status: pending
priority: high
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
tags: [operations, gb10, setup, deployment]
---

# Task: Create setup-gb10.sh One-Shot Deployment Script

## Description

Create a monolithic, idempotent setup script for deploying NATS infrastructure on a fresh Dell DGX Spark GB10 (128GB, Ubuntu 24.04). The script handles the full bootstrap: dependency checking, NATS CLI installation, Docker Compose startup, health wait, and stream provisioning.

## Context

- Target: Dell DGX Spark GB10 running DGX OS (Ubuntu 24.04)
- NATS accessible via Tailscale mesh VPN from all devices
- Docker Compose already defined in repo root (`docker-compose.yml`)
- Existing entrypoint script handles envsubst password injection
- Stream provisioning scripts (`streams/provision-streams.sh`) may not exist yet — handle gracefully

## Reference

- System spec: `docs/design/specs/nats-infrastructure-system-spec.md` (Feature 5)
- Existing scripts: `scripts/docker-entrypoint.sh`, `scripts/verify-nats.sh`

## Acceptance Criteria

- [ ] Script installs NATS CLI via official installer (`https://get-nats.io/install.sh`) if not present
- [ ] Script checks for required dependencies (docker, docker compose, curl) and fails fast with install instructions
- [ ] Script starts NATS via `docker compose up -d` (idempotent — skips if container already running)
- [ ] Script waits for NATS health endpoint (`http://localhost:8222/healthz`) with configurable timeout
- [ ] Script calls `streams/provision-streams.sh` if it exists, logs warning if absent
- [ ] Script runs `scripts/verify-nats.sh` as final verification step
- [ ] Script uses `set -euo pipefail` for error handling
- [ ] Script uses `#!/bin/bash` (not sh) for Ubuntu 24.04 compatibility
- [ ] All configuration values (timeouts, URLs) are environment-variable configurable with sensible defaults
- [ ] Script is executable (`chmod +x`)

## Implementation Notes

Follow the pattern from the system spec Feature 5 `setup-gb10.sh` outline. Use the existing `verify-nats.sh` as the post-setup verification step rather than duplicating checks.
