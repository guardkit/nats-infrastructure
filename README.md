# nats-infrastructure — Ship's Computer Event Bus Deployment

NATS JetStream server configuration, Docker deployment, account management,
and monitoring for the Jarvis Ship's Computer fleet.

## Quick Start

```bash
# 1. Copy .env.example and set real passwords
cp .env.example .env
# Edit .env with your actual passwords (all 4 are required)

# 2. Build and start the NATS server
docker compose up -d --build

# 3. Verify the server is healthy
./scripts/verify-nats.sh

# 4. Check health manually (optional)
curl -sf http://localhost:8222/healthz
```

> **First time?** The `--build` flag builds a custom image from the `Dockerfile`
> (adds `envsubst` to the base `nats:2.11-alpine` image). Subsequent starts can
> omit `--build` unless the Dockerfile or entrypoint script changes.

See [`.env.example`](.env.example) for all required environment variables and their descriptions.

## What's In The Box

- **Docker Compose** — NATS server with JetStream, volume persistence, health checks
- **Dockerfile** — Custom image extending `nats:2.11-alpine` with `envsubst` support
- **Server config** — `nats-server.conf` with JetStream enabled, Tailscale-accessible
- **Account auth** — APPMILLA (Rich + James, full access), FINPROXY (Mark, scoped), SYS (admin)
- **Ops scripts** — verification, health checks

## Dockerfile and Build Context

The service uses a custom Docker image built from the repo-root `Dockerfile`:

```
Dockerfile
├── FROM nats:2.11-alpine          # Base NATS image (pinned major version)
├── RUN apk add --no-cache gettext # Adds envsubst for password template processing
├── COPY scripts/docker-entrypoint.sh  # Custom entrypoint for config templating
├── ENTRYPOINT docker-entrypoint.sh    # Processes account .conf.template files
└── CMD ["-c", "/etc/nats/nats-server.conf"]
```

The `docker-compose.yml` references `build: .` to build from this Dockerfile.
A `.dockerignore` excludes `.git`, `docs/`, `tasks/`, `.claude/`, `.guardkit/`,
`tests/`, and other non-runtime files to keep the build context small.

### How Password Injection Works

1. `.env` passwords are loaded into the container via `env_file: .env`
2. `docker-entrypoint.sh` validates all 4 required password variables
3. `envsubst` processes `config/accounts/accounts.conf.template` → live config
4. NATS server starts with the processed configuration

## Health Check Verification

The Docker Compose health check runs automatically:

```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:8222/healthz"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 5s
```

### Manual Health Check Commands

```bash
# Check container health status
docker compose ps

# Health endpoint (returns HTTP 200 when healthy)
curl -sf http://localhost:8222/healthz

# JetStream status (memory and storage info)
curl -sf http://localhost:8222/jsz | jq

# Server info (name, version, uptime)
curl -sf http://localhost:8222/varz | jq '.server_name, .version, .uptime'

# Run the full verification script
./scripts/verify-nats.sh
```

## Volume Management

JetStream data is persisted in a Docker named volume `nats-data`, mounted at
`/data/jetstream` inside the container.

> **WARNING**: Running `docker compose down -v` **destroys the `nats-data` volume
> and all JetStream data** (streams, consumers, messages, KV buckets). This is
> **irreversible**. Only use `-v` when you intentionally want a clean slate.

### Stopping Without Data Loss

```bash
# Stop the server — data is preserved in the nats-data volume
docker compose down

# Restart later — all JetStream data intact
docker compose up -d
```

### Resetting All Data

```bash
# WARNING: This destroys ALL JetStream data permanently
docker compose down -v
```

### Backup

```bash
# Create a backup of the JetStream data volume
docker run --rm \
  -v nats-infrastructure_nats-data:/data \
  -v "$(pwd)/backups":/backup \
  alpine tar czf /backup/nats-data-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

### Restore

```bash
# Stop NATS first
docker compose down

# Restore from a backup (replace FILENAME with actual backup file)
docker run --rm \
  -v nats-infrastructure_nats-data:/data \
  -v "$(pwd)/backups":/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/FILENAME.tar.gz -C /data"

# Restart NATS
docker compose up -d
```

### Inspecting Volume Contents

```bash
# List files in the JetStream data volume
docker run --rm \
  -v nats-infrastructure_nats-data:/data \
  alpine ls -la /data
```

## Ports

| Port | Purpose |
|------|---------|
| 4222 | Client connections (all agents, adapters, services) |
| 8222 | Monitoring HTTP API (dashboard, health checks) |

## Docs

- `docs/design/specs/nats-infrastructure-system-spec.md` — Full spec
- `docs/design/decisions/ADR-001-standalone-infra-repo.md` — Why standalone, not co-located
- `docs/design/decisions/ADR-002-account-multi-tenancy.md` — NATS accounts for project isolation

## Part of the Jarvis Fleet

This is the backbone. Every agent, adapter, and service connects to it.
Infrastructure changes here affect the entire fleet.
