# nats-infrastructure — System Specification

## For: `/feature-plan` session · guardkit/nats-infrastructure repo · April 2026

---

## What is nats-infrastructure?

The deployment and configuration layer for the NATS JetStream server that underpins
the entire Jarvis Ship's Computer fleet. This repo contains no application code — only
server configuration, Docker Compose definitions, stream provisioning scripts, account
management, and monitoring setup.

This is the backbone middleware. Every agent, adapter, and service connects to it.

---

## Deployment Target

**Primary:** Dell DGX Spark GB10 (128GB) running DGX OS (Ubuntu 24.04).
NATS is accessible via Tailscale mesh VPN from all devices.

| Machine | NATS Role |
|---------|----------|
| **GB10** | NATS server (port 4222), monitoring (port 8222) |
| **MacBook Pro M2 Max** | Client (CLI adapter, dashboard, cloud API calls) |
| **Synology NAS** | JetStream data backup (optional) |

---

## Resolved Decisions (from existing architecture)

| # | Decision | Resolution | Source |
|---|----------|-----------|--------|
| ADR-SP-001 | NATS over Kafka/Redis | NATS JetStream — single binary, sub-ms latency | Dev Pipeline System Spec |
| ADR-SP-002 | State ownership | NATS event bus owns workflow state transitions | Dev Pipeline System Spec |
| ADR-SP-007 | Multi-tenancy | NATS accounts with scoped permissions per project | Dev Pipeline System Spec |
| D4 | Event bus | NATS JetStream (fleet-wide) | Fleet Master Index |

---

## Repository Structure

```
nats-infrastructure/
├── docker-compose.yml            # NATS server (always on)
├── compose/
│   ├── docker-compose.fleet.yml    # Agent fleet (extends base)
│   └── docker-compose.adapters.yml # Adapters — Telegram, Reachy, etc. (extends base)
├── config/
│   ├── nats-server.conf          # Main server configuration
│   ├── accounts/
│   │   ├── appmilla.conf         # APPMILLA account (Rich, James — full access)
│   │   └── finproxy.conf         # FINPROXY account (Mark — scoped to finproxy.>)
│   └── jetstream.conf            # JetStream storage and limits
├── streams/
│   ├── provision-streams.sh      # Script to create JetStream streams
│   └── stream-definitions.json   # Declarative stream configs
├── monitoring/
│   ├── nats-surveyor.yml         # Optional Prometheus metrics
│   └── dashboards/               # Grafana dashboards (future)
├── scripts/
│   ├── setup-gb10.sh             # One-shot setup for GB10
│   ├── backup-jetstream.sh       # Backup JetStream data to NAS
│   ├── health-check.sh           # Quick health verification
│   └── fleet-status.sh           # Show registered agents + status
├── docs/
│   └── design/
│       ├── specs/
│       │   └── nats-infrastructure-system-spec.md  # THIS DOCUMENT
│       └── decisions/
└── README.md
```

---

## Feature 1: NATS Server Configuration

### nats-server.conf

```conf
# Appmilla Ship's Computer — NATS Server Configuration
# Deployed on: Dell DGX Spark GB10

# Server identity
server_name: ships-computer

# Client connections
port: 4222
max_payload: 1MB

# Monitoring
http_port: 8222

# Logging
log_file: "/var/log/nats/nats-server.log"
logtime: true
debug: false
trace: false

# JetStream
jetstream {
    store_dir: "/data/jetstream"
    max_mem: 1GB
    max_file: 10GB
}

# Include accounts
include "accounts/*.conf"

# Tailscale binding — listen on all interfaces
# (Tailscale handles access control at network level)
listen: "0.0.0.0:4222"
http: "0.0.0.0:8222"
```

### Tasks

```
TASK-1: Create nats-server.conf with JetStream enabled
TASK-2: Create docker-compose.yml with NATS server, volume mounts, restart policy
TASK-3: Create setup-gb10.sh for one-shot deployment on GB10
TASK-4: Verify NATS starts, JetStream initialises, monitoring endpoint responds
```

---

## Feature 2: Account-Based Multi-Tenancy

NATS accounts isolate projects so that scoped users (e.g., Mark on FinProxy) can only
see their project's topics.

### Account Structure

| Account | Users | Permissions | Purpose |
|---------|-------|-------------|---------|
| APPMILLA | rich, james | publish: `>`, subscribe: `>` | Full access, all projects |
| FINPROXY | mark, rich_finproxy | publish: `finproxy.>`, subscribe: `finproxy.>` | FinProxy LPA Platform (client-scoped) |
| SYS | admin | system account | NATS administration |

### accounts/appmilla.conf

```conf
accounts {
    APPMILLA {
        users = [
            { user: "rich", password: "$RICH_NATS_PASSWORD" }
            { user: "james", password: "$JAMES_NATS_PASSWORD" }
        ]
        jetstream: enabled
    }
    FINPROXY {
        users = [
            { user: "mark", password: "$MARK_NATS_PASSWORD",
              permissions: {
                  publish: { allow: "finproxy.>" }
                  subscribe: { allow: "finproxy.>" }
              }
            }
        ]
        jetstream: enabled
    }
    SYS {
        users = [
            { user: "admin", password: "$ADMIN_NATS_PASSWORD" }
        ]
    }
}

system_account: SYS
```

### Tasks

```
TASK-5: Create account configuration files with password placeholders
TASK-6: Create .env.example with all required password variables
TASK-7: Test that APPMILLA account can publish/subscribe to all topics
TASK-8: Test that FINPROXY account can ONLY access finproxy.> topics
TASK-9: Test that FINPROXY account CANNOT subscribe to pipeline.> or agents.>
```

---

## Feature 3: JetStream Stream Definitions

Streams define which topics are persisted, with what retention, and for how long.

### Stream Definitions

| Stream | Subjects | Retention | Max Age | Max Messages | Purpose |
|--------|----------|-----------|---------|-------------|---------|
| PIPELINE | `pipeline.>` | WorkQueue | 7 days | 10,000 | Dev pipeline events — feature planning through build completion |
| AGENTS | `agents.>` | Limits | 24 hours | 5,000 | Agent status, approval requests/responses, commands, results |
| JARVIS | `jarvis.>` | Limits | 1 hour | 1,000 | Intent classification, dispatch, routing — high volume, short lived |
| NOTIFICATIONS | `notifications.>` | WorkQueue | 24 hours | 1,000 | Outbound notifications to adapters |
| SYSTEM | `system.>` | Limits | 1 hour | 500 | Health checks, config updates |
| FLEET | `fleet.>` | Limits | 1 hour | 5,000 | Agent registration, deregistration, heartbeats |

### Project-Scoped Streams (Per Client)

| Stream | Subjects | Retention | Purpose |
|--------|----------|-----------|---------|
| FINPROXY | `finproxy.>` | WorkQueue | All FinProxy events — isolated from main streams |

### provision-streams.sh

```bash
#!/bin/bash
# Provision JetStream streams for the Ship's Computer fleet
# Run once after NATS server starts, or after stream definition changes

NATS_URL="${NATS_URL:-nats://localhost:4222}"
NATS_CREDS="${NATS_CREDS:-}"

nats_cmd="nats --server $NATS_URL"
[ -n "$NATS_CREDS" ] && nats_cmd="$nats_cmd --creds $NATS_CREDS"

echo "Provisioning JetStream streams..."

$nats_cmd stream add PIPELINE \
    --subjects "pipeline.>" \
    --retention work \
    --max-age 7d \
    --max-msgs 10000 \
    --storage file \
    --replicas 1 \
    --defaults

$nats_cmd stream add AGENTS \
    --subjects "agents.>" \
    --retention limits \
    --max-age 24h \
    --max-msgs 5000 \
    --storage file \
    --replicas 1 \
    --defaults

$nats_cmd stream add FLEET \
    --subjects "fleet.>" \
    --retention limits \
    --max-age 1h \
    --max-msgs 5000 \
    --storage file \
    --replicas 1 \
    --defaults

# ... etc for each stream

echo "Streams provisioned successfully."
$nats_cmd stream ls
```

### Tasks

```
TASK-10: Create stream-definitions.json with all stream configs
TASK-11: Create provision-streams.sh that reads definitions and creates streams
TASK-12: Make provision idempotent (skip existing streams or update them)
TASK-13: Add project-scoped stream creation for new client projects
TASK-14: Test stream retention — publish messages, verify max-age expiry
```

---

## Feature 4: Docker Compose Deployment

### docker-compose.yml

```yaml
version: '3.8'

services:
  nats:
    image: nats:latest
    container_name: ships-computer-nats
    restart: unless-stopped
    ports:
      - "4222:4222"   # Client connections
      - "8222:8222"   # Monitoring / HTTP API
    volumes:
      - ./config/nats-server.conf:/etc/nats/nats-server.conf:ro
      - ./config/accounts:/etc/nats/accounts:ro
      - nats-data:/data/jetstream
    command: ["-c", "/etc/nats/nats-server.conf"]
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    env_file:
      - .env

volumes:
  nats-data:
    driver: local
```

### Tasks

```
TASK-15: Create docker-compose.yml with NATS server, JetStream volume, health check
TASK-16: Create .env.example with all required environment variables
TASK-17: Test docker compose up — NATS starts, JetStream initialises, healthcheck passes
TASK-18: Test docker compose down + up — JetStream data survives restart (volume persistence)
TASK-19: Add docker compose profile for monitoring stack (optional, future)
```

---

## Feature 5: Operations Scripts

### setup-gb10.sh

One-shot script for deploying NATS on a fresh GB10:

```bash
#!/bin/bash
# Setup NATS infrastructure on Dell DGX Spark GB10
set -euo pipefail

echo "=== Ship's Computer NATS Infrastructure Setup ==="

# 1. Install nats CLI tool
curl -fsSL https://get-nats.io/install.sh | sh

# 2. Start NATS via Docker Compose
docker compose up -d

# 3. Wait for health
echo "Waiting for NATS to be healthy..."
until curl -sf http://localhost:8222/healthz > /dev/null; do
    sleep 1
done

# 4. Provision JetStream streams
./streams/provision-streams.sh

# 5. Verify
nats server info
nats stream ls
echo "=== NATS infrastructure ready ==="
```

### health-check.sh

Quick verification script:

```bash
#!/bin/bash
echo "NATS Server:"
curl -sf http://localhost:8222/varz | jq '{server_name, version, jetstream}'
echo ""
echo "JetStream Streams:"
nats stream ls --json | jq '.[].config.name'
echo ""
echo "Connected Clients:"
curl -sf http://localhost:8222/connz | jq '.num_connections'
```

### backup-jetstream.sh

Backup JetStream data to Synology NAS:

```bash
#!/bin/bash
BACKUP_DIR="/volume1/backups/nats/$(date +%Y%m%d)"
rsync -avz /data/jetstream/ nas.tail:$BACKUP_DIR/
echo "JetStream backed up to $BACKUP_DIR"
```

### Tasks

```
TASK-20: Create setup-gb10.sh with NATS CLI install, compose up, stream provision
TASK-21: Create health-check.sh with server info, stream list, client count
TASK-22: Create backup-jetstream.sh with rsync to NAS
TASK-23: Test full setup-gb10.sh on clean Docker environment
```

---

## Feature 6: KV Stores for Agent State

NATS JetStream KV provides lightweight key-value storage for agent runtime state.

### KV Buckets

| Bucket | Purpose | TTL |
|--------|---------|-----|
| `agent-status` | Last known status per agent (replaces polling) | None (persistent) |
| `agent-registry` | Fleet routing table — agent capability manifests, updated on register/deregister. Jarvis reads this for routing. Survives Jarvis restarts. | None (persistent) |
| `pipeline-state` | Current pipeline state per feature_id | 7 days |
| `jarvis-session` | Jarvis conversation session context | 1 hour |

### Tasks

```
TASK-24: Add KV bucket creation to provision-streams.sh
TASK-25: Document KV usage patterns in README (get/put/watch)
TASK-26: Test KV watch — agent publishes status, dashboard watches for updates
TASK-27: Create agent-registry KV bucket in provision-streams.sh
TASK-28: Test KV watch on agent-registry — Jarvis watches for registration changes
```

---

## Feature 7: Agent Fleet Compose

Docker Compose configuration for running containerised agents alongside the NATS
infrastructure. This enables concurrent multi-agent execution with clean lifecycle
management.

### Why Containers Now (Revised Decision)

The original decision (D14) deferred containerisation to Phase 10+. The CAN bus
registration pattern changes the calculus: with dynamic agent discovery, containers
become the natural lifecycle management unit. `docker compose up` brings agents online,
they auto-register with Jarvis, `docker compose down` triggers graceful deregistration.

Additionally, running multiple agent instances in parallel (e.g., two GuardKit Factory
instances for concurrent project builds) requires process isolation that containers
provide naturally.

### Architecture

```
nats-infrastructure/
├── docker-compose.yml              ← NATS server (existing)
└── compose/
    ├── docker-compose.fleet.yml    ← Agent fleet (extends base)
    └── docker-compose.adapters.yml ← Adapters (extends base)
```

**Two-file compose pattern:** The base `docker-compose.yml` runs NATS server only
(always on). Agent and adapter compose files extend it and can be started/stopped
independently.

### compose/docker-compose.fleet.yml

```yaml
# Agent fleet — start/stop agents independently of NATS server
# Usage: docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml up

services:
  jarvis-router:
    image: guardkit/jarvis:latest
    container_name: jarvis-router
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=jarvis-router
    restart: unless-stopped
    networks:
      - ships-computer

  guardkitfactory:
    image: guardkit/guardkitfactory:latest
    container_name: guardkitfactory
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=guardkitfactory
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    deploy:
      replicas: 1  # Scale to 2 for parallel project builds
    restart: unless-stopped
    networks:
      - ships-computer

  ideation-agent:
    image: guardkit/ideation-agent:latest
    container_name: ideation-agent
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=ideation-agent
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
    networks:
      - ships-computer

  product-owner-agent:
    image: guardkit/product-owner-agent:latest
    container_name: product-owner-agent
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=product-owner-agent
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
    networks:
      - ships-computer

  architect-agent:
    image: guardkit/architect-agent:latest
    container_name: architect-agent
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=architect-agent
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
    networks:
      - ships-computer

  general-purpose-agent:
    image: guardkit/general-purpose-agent:latest
    container_name: general-purpose-agent
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - NATS_URL=nats://nats:4222
      - AGENT_ID=general-purpose-agent
    restart: unless-stopped
    networks:
      - ships-computer

networks:
  ships-computer:
    name: ships-computer
    external: true  # Created by base docker-compose.yml
```

### Scaling Pattern

```bash
# Start the full fleet
docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml up -d

# Scale GuardKit Factory for parallel project builds
docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml \
    up -d --scale guardkitfactory=2

# Each instance auto-registers with Jarvis via fleet.register
# Jarvis routes to the instance with lowest queue_depth

# Start just specific agents
docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml \
    up -d jarvis-router guardkitfactory ideation-agent
```

### Agent Container Lifecycle → NATS Registration

Each agent container follows this lifecycle:

```
Container starts
  → Agent process starts
  → Connects to NATS at nats://nats:4222
  → Publishes AgentRegistrationPayload to fleet.register
  → Begins heartbeating to fleet.heartbeat.{agent_id} every 30s
  → Ready to receive dispatched work

Container stopping (SIGTERM)
  → Agent catches signal
  → Publishes AgentDeregistrationPayload to fleet.deregister
  → Drains active NATS subscriptions
  → Process exits
  → Container stops

Container crashed (unexpected)
  → Heartbeat stops
  → After 90s, Jarvis marks agent as unavailable
  → docker compose restart policy recreates container
  → Agent re-registers on startup
```

### Tasks

```
TASK-29: Create compose/docker-compose.fleet.yml with all agent services
TASK-30: Create compose/docker-compose.adapters.yml with adapter services
TASK-31: Update base docker-compose.yml to create ships-computer network
TASK-32: Test fleet startup — all agents register with Jarvis
TASK-33: Test graceful shutdown — agents deregister on docker compose down
TASK-34: Test scaling — docker compose up --scale guardkitfactory=2
TASK-35: Test crash recovery — kill a container, verify heartbeat timeout + restart
TASK-36: Create fleet.env.example with all API keys and agent config
```

---

## Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| NATS starts in < 5 seconds | Fast restart after GB10 reboot | Single binary, minimal config |
| JetStream data survives container restart | No data loss | Docker volume mount |
| Monitoring endpoint always available | Dashboard + health checks | Port 8222 health/varz/connz |
| Account isolation verified by test | Security boundary | Mark cannot see non-FinProxy topics |
| Backup to NAS automated | Disaster recovery | rsync to Synology DS918+ |

---

## Port Allocation on GB10 (Updated)

| Port | Service | Used By |
|------|---------|---------|
| 4222 | NATS server (client connections) | All agents, adapters, clients |
| 8222 | NATS monitoring (HTTP API) | Dashboard, health checks |
| 8000 | Graphiti LLM (Qwen2.5-14B) | Graphiti entity extraction |
| 8001 | Embedding model (nomic-embed) | Graphiti + ChromaDB |
| 8002 | AutoBuild LLM (Qwen3-Coder-Next) | Implementation model (local mode) |

---

## Build Approach

This repo is config/ops, not application code — `/feature-plan` is more appropriate
than `/feature-spec` (no complex behavioural contracts, just deployment tasks).

```bash
# 1. Bootstrap repo structure
cd ~/Projects/appmilla_github/nats-infrastructure
# (Already done — docs/design/specs/ and docs/design/decisions/ exist)

# 2. Run /feature-plan with this spec as context
/feature-plan --context docs/design/specs/nats-infrastructure-system-spec.md

# 3. Work through tasks sequentially
# TASK-1 through TASK-4: Server config + Docker
# TASK-5 through TASK-9: Account auth
# TASK-10 through TASK-14: JetStream streams
# TASK-15 through TASK-19: Docker Compose
# TASK-20 through TASK-23: Ops scripts
# TASK-24 through TASK-28: KV stores + agent registry
# TASK-29 through TASK-36: Agent fleet compose
```
