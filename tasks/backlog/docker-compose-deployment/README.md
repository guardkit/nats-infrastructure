# Feature: Docker Compose Deployment

**ID**: FEAT-DCD | **Review**: TASK-REV-1A6B | **Complexity**: 4/10 | **Tasks**: 5

## Problem

The nats-infrastructure repo has server configuration (`nats-server.conf`), account templates, and an entrypoint script — but no Docker Compose file to actually run NATS. The deployment target (Dell DGX Spark GB10) needs a single `docker compose up -d` command to bring NATS online with JetStream persistence and health monitoring.

## Solution

Create `docker-compose.yml` and a thin `Dockerfile` that:
- Runs NATS 2.11 (Alpine) with JetStream enabled
- Uses the existing `docker-entrypoint.sh` for secure password injection via envsubst
- Persists JetStream data in a named Docker volume (`nats-data`)
- Health checks via the monitoring endpoint (`:8222/healthz`)
- Creates a custom network (`ships-computer`) for future fleet compose extension

## Tasks

| Wave | Task | Name | Mode | Complexity |
|------|------|------|------|-----------|
| 1 | TASK-DCD-001 | Create docker-compose.yml | task-work | 3 |
| 1 | TASK-DCD-002 | Create Dockerfile with envsubst | task-work | 3 |
| 2 | TASK-DCD-003 | Verify compose up + health check | direct | 2 |
| 2 | TASK-DCD-004 | Verify volume persistence | direct | 2 |
| 2 | TASK-DCD-005 | Update README | direct | 1 |

## Getting Started

1. Review [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for architecture decisions and diagrams
2. Start with Wave 1 tasks (TASK-DCD-001 and TASK-DCD-002 can run in parallel)
3. After Wave 1, run Wave 2 verification and documentation tasks
