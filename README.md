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
- **JetStream streams** — 6 core + project streams and KV buckets with idempotent provisioning

## JetStream Streams

All JetStream streams and KV buckets are defined declaratively in
[`streams/stream-definitions.json`](streams/stream-definitions.json) and provisioned
by the idempotent [`streams/provision-streams.sh`](streams/provision-streams.sh) script.

### Core Streams

| Stream | Subjects | Retention | Max Age | Description |
|--------|----------|-----------|---------|-------------|
| PIPELINE | `pipeline.>` | work | 7d | Dev pipeline events — feature planning through build completion |
| AGENTS | `agents.>` | limits | 24h | Agent status, approval requests/responses, commands, results |
| JARVIS | `jarvis.>` | limits | 1h | Intent classification, dispatch, routing — high volume, short lived |
| NOTIFICATIONS | `notifications.>` | work | 24h | Outbound notifications to adapters |
| SYSTEM | `system.>` | limits | 1h | Health checks, config updates |
| FLEET | `fleet.>` | limits | 1h | Agent registration, deregistration, heartbeats |

### Project Streams

| Stream | Subjects | Retention | Max Age | Description |
|--------|----------|-----------|---------|-------------|
| FINPROXY | `finproxy.>` | work | 24h | All FinProxy events — isolated from main streams |

Project streams are scoped to individual client accounts. FINPROXY is isolated to the
FINPROXY NATS account (Mark), enforced at the account permission level.

### KV Buckets

JetStream KV buckets provide key-value storage backed by streams. They are defined in
the `kv_buckets` array of `stream-definitions.json` and provisioned alongside streams.

| Bucket | TTL | Storage | History | Description |
|--------|-----|---------|---------|-------------|
| agent-status | — | file | 1 | Last known status per agent — replaces polling |
| agent-registry | — | file | 5 | Fleet routing table — agent capability manifests, used by Jarvis for routing |
| pipeline-state | 7d | file | 3 | Current pipeline state per feature_id |
| jarvis-session | 1h | memory | 1 | Jarvis conversation session context |

Buckets with no TTL (`null`) are persistent — keys remain until explicitly deleted.
Buckets with a TTL automatically expire keys after the specified duration. Memory-backed
buckets (`jarvis-session`) do not survive server restarts.

For detailed KV usage patterns, CLI examples, watch patterns, and agent interaction
documentation, see [`docs/kv-usage.md`](docs/kv-usage.md).

### Provisioning Commands

```bash
# Provision all streams and KV buckets (idempotent — safe to run multiple times)
./streams/provision-streams.sh

# Preview what would happen without making changes
./streams/provision-streams.sh --dry-run

# Use a custom NATS URL
NATS_URL=nats://nats:4222 ./streams/provision-streams.sh

# Use credentials file
NATS_CREDS=/path/to/creds.nk ./streams/provision-streams.sh
```

**Prerequisites**: `jq` and the [NATS CLI](https://github.com/nats-io/natscli) must be
installed. The script waits for the NATS server to be healthy before provisioning.

### Idempotency Guarantees

The provisioning script uses a **check-then-create-or-update** pattern that is safe to
run on first deploy, on reboot, and after definition changes. The same idempotency
pattern applies to both streams and KV buckets:

1. **Resource does not exist** → `[CREATE]` — creates the stream or KV bucket with the defined config
2. **Resource exists and config matches** → `[OK]` — no changes made
3. **Resource exists but config differs** → `[UPDATE]` — updates the stream via `nats stream update --force` or the KV bucket via `nats kv update`
4. **Resource operation fails** → `[ERROR]` — logged but does not halt remaining resources

The script always exits 0 unless a fatal error occurs (missing `jq`, unreachable NATS
server, missing definitions file). A summary is printed at the end:

```
Streams:    X created, Y updated, Z already current, W errors
KV Buckets: X created, Y updated, Z already current, W errors
```

### Adding a New Stream

To add a new project stream:

1. **Define the stream** — Add a new entry to `streams/stream-definitions.json`:
   ```json
   {
     "name": "MYPROJECT",
     "subjects": ["myproject.>"],
     "retention": "work",
     "max_age": "24h",
     "max_msgs": 5000,
     "storage": "file",
     "replicas": 1,
     "scope": "project",
     "description": "MyProject events — isolated from main streams"
   }
   ```
2. **Add account permissions** — Update `config/accounts/accounts.conf.template` to
   grant the appropriate NATS account access to the new subject namespace.
3. **Provision** — Run `./streams/provision-streams.sh` (or `--dry-run` to preview).
4. **Update tests** — Add the new stream to the expected streams in
   `tests/test_stream_definitions.py`.

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

- `docs/kv-usage.md` — KV store usage patterns, CLI examples, and agent interaction documentation
- `docs/design/specs/nats-infrastructure-system-spec.md` — Full spec
- `docs/design/decisions/ADR-001-standalone-infra-repo.md` — Why standalone, not co-located
- `docs/design/decisions/ADR-002-account-multi-tenancy.md` — NATS accounts for project isolation

## Part of the Jarvis Fleet

This is the backbone. Every agent, adapter, and service connects to it.
Infrastructure changes here affect the entire fleet.
