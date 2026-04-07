# Feature: NATS Server Configuration

**Feature ID**: FEAT-NATS-CFG
**Parent Review**: TASK-REV-69BD
**Status**: Planned
**Complexity**: 4/10

## Problem Statement

The nats-infrastructure repo needs a NATS server configuration file with JetStream enabled, targeted at Dell DGX Spark GB10 (128GB). The config must support account-based multi-tenancy (APPMILLA full access, FINPROXY scoped to `finproxy.>`), and credentials must not be committed to the repository.

## Solution Approach

**Option 1** (from review): Single `nats-server.conf` with `include` for account configs, using `envsubst` to substitute credentials from `.env` at container startup.

- NATS config does not natively support env var interpolation
- `envsubst` in a Docker entrypoint script solves this cleanly
- Passwords stored in `.env` (gitignored), templates version-controlled

## Tasks

| Wave | Task | Title | Complexity | Mode |
|------|------|-------|-----------|------|
| 1 | TASK-NATS-001 | Create nats-server.conf with JetStream | 3 | task-work |
| 2 | TASK-NATS-002 | Create account configs + entrypoint | 4 | task-work |
| 3 | TASK-NATS-003 | Create .env.example | 2 | direct |
| 4 | TASK-NATS-004 | Verify NATS startup + JetStream | 3 | task-work |

**Execution**: Sequential (each task depends on the previous)
**Estimated Effort**: 2-3 hours total

## Key Decisions

1. **envsubst for credentials** — NATS config doesn't interpolate env vars; entrypoint script handles it
2. **Single accounts file** — 3 accounts doesn't warrant per-account files
3. **1GB mem / 10GB file JetStream limits** — conservative for GB10, easily adjustable
4. **curl-based verification** — no nats CLI dependency for basic health checks

## References

- [System Spec](../../docs/design/specs/nats-infrastructure-system-spec.md) — Feature 1
- [ADR-001](../../docs/design/decisions/ADR-001-standalone-infra-repo.md) — Standalone infra repo
- [ADR-002](../../docs/design/decisions/ADR-002-account-multi-tenancy.md) — Account-based multi-tenancy

## Next Steps

```bash
/task-work TASK-NATS-001   # Start with Wave 1
```
