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
- **Account auth** — APPMILLA (Rich + James, full access), FINPROXY (Mark, scoped), SYS (admin).
  APPMILLA also holds subject-scoped service users: `forge`, `fleet-memory`, `guardkit`, `jarvis` and
  `dashboard_approve` (the factory dashboard's answers to Forge's cards: it may publish only on
  `agents.approval.forge.*.response` and may subscribe to nothing). Nine passwords in all; see
  `config/accounts/accounts.conf.template` and `.env.example`
- **Ops scripts** — verification, health checks
- **JetStream streams** — 6 core + project streams with idempotent provisioning
- **KV buckets** — 4 buckets, created and kept in line with their definitions by `kv/provision-kv.sh`

## JetStream Streams

All JetStream streams are defined declaratively in
[`streams/stream-definitions.json`](streams/stream-definitions.json) and provisioned
by the idempotent [`streams/provision-streams.sh`](streams/provision-streams.sh) script.
KV buckets are defined separately — see [KV Buckets](#kv-buckets).

### Core Streams

| Stream | Subjects | Retention | Max Age | Description |
|--------|----------|-----------|---------|-------------|
| PIPELINE | `pipeline.>` | work | 7d | Dev pipeline events — feature planning through build completion |
| AGENTS | `agents.>` | limits | 24h | Agent status, approval requests/responses, commands, results |
| JARVIS | `jarvis.>` | limits | 1h | Intent classification, dispatch, routing — high volume, short lived |
| NOTIFICATIONS | `notifications.>` | work | 24h | Outbound notifications to adapters |
| SYSTEM | `system.>` | limits | 1h | Health checks, config updates |
| FLEET | `fleet.>` | limits | 1h | Agent registration, deregistration, heartbeats |
| MEMORY | `memory.episode.>`, `memory.dlq.>` | limits | 365d | Durable memory episodes + per-project DLQ; consumed by the fleet-memory relay → Postgres (write-path v2) |

### Project Streams

| Stream | Subjects | Retention | Max Age | Description |
|--------|----------|-----------|---------|-------------|
| FINPROXY | `finproxy.>` | work | 24h | All FinProxy events — isolated from main streams |

Project streams are scoped to individual client accounts. FINPROXY is isolated to the
FINPROXY NATS account (Mark), enforced at the account permission level.

### KV Buckets

JetStream KV buckets provide key-value storage backed by streams. They are defined in
[`kv/kv-definitions.json`](kv/kv-definitions.json) — the only place KV bucket settings
live — and provisioned by [`kv/provision-kv.sh`](kv/provision-kv.sh), which runs after
the streams.

| Bucket | TTL | Storage | History | Max value | Description |
|--------|-----|---------|---------|-----------|-------------|
| agent-status | — | file | 1 | 64KB | Last known status per agent — replaces polling |
| agent-registry | — | file | 5 | 256KB | Fleet routing table — agent capability manifests, used by Jarvis for routing |
| pipeline-state | 7d | file | 3 | 64KB | Current pipeline state per feature_id |
| jarvis-session | 1h | memory | 1 | 128KB | Jarvis conversation session context |

Buckets with no TTL (`null`) are persistent — keys remain until explicitly deleted.
Buckets with a TTL automatically expire keys after the specified duration. Memory-backed
buckets (`jarvis-session`) do not survive server restarts.

For detailed KV usage patterns, CLI examples, watch patterns, and agent interaction
documentation, see [`docs/kv-usage.md`](docs/kv-usage.md).

#### Keeping KV buckets in line with their definitions

`kv/provision-kv.sh` creates any missing bucket with its defined settings. For a bucket
that already exists it reads the live settings and compares them with the definition:

- history, max value size, TTL and replicas are corrected in place with `nats kv edit`,
  and the bucket is read again to confirm the change took (TTL is compared to the
  nanosecond, so a sub-second TTL on a bucket meant to be persistent counts as drift);
- a different **storage type** (file vs memory) cannot be edited — the bucket has to be
  deleted and recreated, which loses its values — so the script refuses by default and
  says so. Pass `--recreate <bucket>` to allow exactly that bucket to be recreated.

```bash
# Show what would change, without changing anything (reads the live buckets)
./kv/provision-kv.sh --dry-run

# Apply: create missing buckets, correct drifted settings
./kv/provision-kv.sh

# Also allow jarvis-session to be deleted and recreated to change its storage type
./kv/provision-kv.sh --recreate jarvis-session
```

If the live settings come back incomplete or invalid (a missing or unknown storage type,
a missing or non-integer history, TTL or replica count), that bucket is reported as an
error and left untouched — even when `--recreate` names it.

The script exits non-zero if any bucket could not be read, created or corrected, or was
refused; `--dry-run` exits the same way the real run would.

> **Changed (September 2026):** `streams/provision-streams.sh` used to create the KV
> buckets too, from its own list, with default settings (history 1, no size limit, file
> storage). Because it ran first, those defaults won, and `kv/provision-kv.sh` then
> tried to correct them with `nats kv update` — a command that updates a key, not a
> bucket — failed, and still reported success. The live buckets drifted from their
> definitions as a result. Now only `kv/provision-kv.sh` creates KV buckets, it uses
> `nats kv edit`, and it fails loudly.

### Provisioning Commands

```bash
# Provision all streams (idempotent — safe to run multiple times)
./streams/provision-streams.sh

# Then provision KV buckets
./kv/provision-kv.sh

# Preview what would happen without making changes
./streams/provision-streams.sh --dry-run
./kv/provision-kv.sh --dry-run

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
3. **Resource exists but config differs** → `[UPDATE]` — updates the stream via `nats stream update --force` or the KV bucket via `nats kv edit`
4. **Resource operation fails** → `[ERROR]` — logged but does not halt remaining resources

`provision-streams.sh` exits 0 unless a fatal error occurs (missing `jq`, unreachable
NATS server, missing definitions file). `provision-kv.sh` additionally exits non-zero
when any bucket has an `[ERROR]` or is `[REFUSED]`. Each prints a summary at the end:

```
Streams:    X created, Y updated, Z already current, W errors
KV Buckets: X created, Y updated, R recreated, Z already current, W errors (N refused)
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
2. `docker-entrypoint.sh` validates the 4 core password variables up front
3. `envsubst` processes `config/accounts/accounts.conf.template` → live config, substituting only the
   nine named `*_NATS_PASSWORD` variables; a missing one leaves an empty password or an unresolved
   `${VAR}`, and the entrypoint refuses to start
4. NATS server starts with the processed configuration

### Upgrading when an account password is added (release order)

The template is read from the checkout (compose mounts `./config/accounts`), but the entrypoint, with its fixed list
of password names, is built into the image. An old image with a new template leaves the new `${NAME}` unsubstituted,
and the broker refuses to start: not at once, but at its next restart or reboot. So, for example for
`DASHBOARD_APPROVE_NATS_PASSWORD` (19 October 2026):

1. **Add the new key to the broker's encrypted env file first.** An extra variable is harmless to the old image.
2. **Then pull, rebuild the image and recreate the broker, as one step**, under `sops exec-env`
   (`docker compose up -d --build --force-recreate nats`), in an idle window.
3. **Never `git pull` on its own** in the checkout the live broker runs from.

If step 1 was missed, the broker refuses to start and names the missing variable.

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
