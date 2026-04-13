# Feature: Operations Scripts

## Problem

The nats-infrastructure repo provides Docker Compose deployment and server configuration, but lacks operational scripts for day-to-day management of the NATS infrastructure on the GB10. Operators need one-command setup, quick health verification, and automated backup to the Synology NAS.

## Solution

Three shell scripts covering the operational lifecycle:

1. **setup-gb10.sh** — One-shot deployment on a fresh GB10 (install deps, start NATS, provision streams, verify)
2. **health-check.sh** — Quick operational probe (server status, JetStream usage, client count)
3. **backup-jetstream.sh** — Incremental backup of JetStream data to Synology NAS via rsync

## Tasks

| ID | Title | Complexity | Wave | Status |
|----|-------|------------|------|--------|
| TASK-OPS-001 | Create setup-gb10.sh | 4/10 | 1 | pending |
| TASK-OPS-002 | Create health-check.sh | 2/10 | 1 | pending |
| TASK-OPS-003 | Create backup-jetstream.sh | 3/10 | 1 | pending |
| TASK-OPS-004 | Test operations scripts | 3/10 | 2 | pending |

## Key Decisions

- **Monolithic setup** over modular sub-scripts — one-shot operation doesn't benefit from modularity
- **curl-based health** over nats CLI — simpler, faster, no auth dependency for monitoring endpoints
- **rsync to NAS** over Docker volume backup — no downtime required, incremental transfers
- All scripts follow existing conventions from `verify-nats.sh` and `docker-entrypoint.sh`

## Parent Review

[TASK-REV-2462](../TASK-REV-2462-plan-operations-scripts.md)
