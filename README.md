# nats-infrastructure — Ship's Computer Event Bus Deployment

NATS JetStream server configuration, Docker deployment, stream provisioning, account
management, and monitoring for the Jarvis Ship's Computer fleet.

## Status: Pre-Implementation

System spec ready at `docs/design/specs/nats-infrastructure-system-spec.md`.
This is config/ops — use `/feature-plan` for task breakdown, then work through tasks.

## Quick Start (GB10)

```bash
# One-shot setup
./scripts/setup-gb10.sh

# Or manually
docker compose up -d
./streams/provision-streams.sh
./scripts/health-check.sh
```

## What's In The Box

- **Docker Compose** — NATS server with JetStream, volume persistence, health checks
- **Server config** — `nats-server.conf` with JetStream enabled, Tailscale-accessible
- **Account auth** — APPMILLA (Rich + James, full access), FINPROXY (Mark, scoped), SYS (admin)
- **Stream definitions** — PIPELINE, AGENTS, JARVIS, NOTIFICATIONS, SYSTEM + per-project streams
- **KV buckets** — agent-status, pipeline-state, jarvis-session
- **Ops scripts** — setup, health check, JetStream backup to NAS

## Ports

| Port | Purpose |
|------|---------|
| 4222 | Client connections (all agents, adapters, services) |
| 8222 | Monitoring HTTP API (dashboard, health checks) |

## Docs

- `docs/design/specs/nats-infrastructure-system-spec.md` — Full spec with 6 features, 26 tasks
- `docs/design/decisions/ADR-001-standalone-infra-repo.md` — Why standalone, not co-located
- `docs/design/decisions/ADR-002-account-multi-tenancy.md` — NATS accounts for project isolation

## Part of the Jarvis Fleet

This is the backbone. Every agent, adapter, and service connects to it.
Infrastructure changes here affect the entire fleet.
