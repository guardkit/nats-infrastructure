# Implementation Guide: Docker Compose Deployment

**Feature**: NATS server with JetStream, volume persistence, health checks
**Feature ID**: FEAT-DCD
**Parent Review**: TASK-REV-1A6B
**Approach**: Single docker-compose.yml with Custom Entrypoint (Option 1)
**Overall Complexity**: 4/10
**Tasks**: 5

---

## Data Flow: Read/Write Paths

This is the primary review artefact. It shows how configuration flows from host files through Docker into the running NATS server, and how JetStream data persists via the named volume.

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["docker-entrypoint.sh\n(envsubst processing)"]
        W2["nats-server\n(JetStream writes)"]
        W3["docker compose up\n(container lifecycle)"]
    end

    subgraph Storage["Storage"]
        S1[("accounts.conf\n(in-container, generated)")]
        S2[("/data/jetstream\n(named volume: nats-data)")]
        S3[("container state\n(Docker engine)")]
    end

    subgraph Reads["Read Paths"]
        R1["nats-server\n(reads accounts.conf)"]
        R2["nats-server\n(reads/writes JetStream)"]
        R3["healthcheck\n(wget :8222/healthz)"]
        R4["clients\n(port 4222)"]
        R5["monitoring\n(port 8222 /varz /connz)"]
    end

    W1 -->|"envsubst .template → .conf"| S1
    W2 -->|"stream/consumer data"| S2
    W3 -->|"start/stop/restart"| S3

    S1 -->|"include accounts/*.conf"| R1
    S2 -->|"file-based storage"| R2
    S3 -->|"HTTP :8222"| R3
    S3 -->|"TCP :4222"| R4
    S3 -->|"HTTP :8222"| R5

    style R1 fill:#cfc,stroke:#090
    style R2 fill:#cfc,stroke:#090
    style R3 fill:#cfc,stroke:#090
    style R4 fill:#cfc,stroke:#090
    style R5 fill:#cfc,stroke:#090
```

_All write paths have corresponding read paths. No disconnections detected._

---

## Task Dependencies

```mermaid
graph TD
    T1[TASK-DCD-001: Create docker-compose.yml] --> T3[TASK-DCD-003: Verify compose up]
    T2[TASK-DCD-002: Create Dockerfile] --> T3
    T1 --> T4[TASK-DCD-004: Verify volume persistence]
    T2 --> T4
    T1 --> T5[TASK-DCD-005: Update README]
    T2 --> T5

    style T1 fill:#cfc,stroke:#090
    style T2 fill:#cfc,stroke:#090
```

_Tasks with green background can run in parallel._

---

## Execution Strategy

### Wave 1: Foundation (2 tasks, parallel)

Both scaffolding tasks can run in parallel — they produce separate files (`docker-compose.yml` and `Dockerfile`) with a known coordination point (compose references the Dockerfile via `build: .`).

| Task | Name | Mode | Complexity |
|------|------|------|-----------|
| TASK-DCD-001 | Create docker-compose.yml | task-work | 3/10 |
| TASK-DCD-002 | Create Dockerfile | task-work | 3/10 |

**Coordination**: TASK-DCD-001 should use `build: .` in the service definition, anticipating the Dockerfile from TASK-DCD-002. If implementing sequentially, TASK-DCD-001 first.

### Wave 2: Verification + Documentation (3 tasks, parallel)

All three depend on Wave 1 completion. Testing tasks require a running Docker environment on the GB10 or local machine. Documentation can run in parallel with testing.

| Task | Name | Mode | Complexity |
|------|------|------|-----------|
| TASK-DCD-003 | Verify compose up | direct | 2/10 |
| TASK-DCD-004 | Verify volume persistence | direct | 2/10 |
| TASK-DCD-005 | Update README | direct | 1/10 |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Image | `nats:2.11-alpine` | Pinned major avoids breaking changes; Alpine for small footprint |
| Volume | Named volume `nats-data` | Docker-managed, survives `docker compose down`, easy backup |
| Health check | `wget --spider :8222/healthz` | Built into Alpine, fast, reliable |
| Start period | 5 seconds | JetStream file store needs init time |
| Restart | `unless-stopped` | Survives reboot, respects manual `docker stop` |
| Network | Custom `ships-computer` | Fleet compose files join this network (Feature 7) |
| Passwords | envsubst in entrypoint | Already implemented; validates all 4 vars before start |
| Config mounts | Read-only (`:ro`) | Prevents accidental container-side config writes |
| Dockerfile | Custom with `gettext` | Guarantees `envsubst` availability regardless of base image changes |

---

## File Mapping

| File | Created By | Purpose |
|------|-----------|---------|
| `docker-compose.yml` | TASK-DCD-001 | NATS service definition, volumes, networks |
| `Dockerfile` | TASK-DCD-002 | Custom image with envsubst support |
| `.dockerignore` | TASK-DCD-002 | Exclude non-build files from Docker context |
| `README.md` | TASK-DCD-005 | Updated deployment instructions |

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| `wget` removed from future NATS Alpine | Dockerfile controls the image; can add `wget` explicitly |
| JetStream data loss on `down -v` | TASK-DCD-005 documents the warning prominently in README |
| Port conflicts on GB10 | 4222/8222 are NATS-standard; documented in system spec |
| envsubst breaks on special chars in passwords | entrypoint.sh already uses `set -eu` for error handling |

---

## Prerequisites

- Docker and Docker Compose v2 installed on target machine
- `.env` file with 4 required password variables (copy from `.env.example`)
- Ports 4222 and 8222 available
- `nats` CLI tool for verification tasks (TASK-DCD-003, TASK-DCD-004)
