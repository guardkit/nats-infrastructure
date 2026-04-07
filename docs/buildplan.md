# nats-infrastructure — Build Plan

## GuardKit Command Sequence for Building nats-infrastructure

**Repo:** `/Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure`
**Template:** `nats-asyncio-service` (initialised via `guardkit init`)
**Spec:** `docs/design/specs/nats-infrastructure-system-spec.md` (7 features, 36 tasks)

---

## Pre-Flight Check

Before running commands, verify:
- [x] `guardkit init nats-asyncio-service` completed
- [x] Spec merged (no addendum files — Feature 7 fleet compose already in main spec)
- [x] ADRs in place (2 decision records in `docs/design/decisions/`)
- [x] Graphiti knowledge graph seeded (project overview, ADRs, feature review)
- [ ] Docker available on GB10 (`docker info`)
- [ ] NATS CLI installed or installable (`brew install nats-io/nats-tools/nats`)

---

## Approach: /feature-plan (Not /feature-spec)

nats-infrastructure is config/ops — Docker Compose files, server configuration,
shell scripts, stream provisioning. There are no complex behavioural contracts
requiring BDD scenarios. `/feature-plan` with task-oriented breakdown is the
right command.

We skip `/system-arch` and `/system-design` because:
- This isn't application architecture — it's deployment configuration
- The architecture decisions are already captured in the ADRs
- The system spec already defines everything needed for implementation

---

## Phase 1: Core Infrastructure (Features 1-4)

These features produce the running NATS server that everything else depends on.

### Feature 1 — NATS Server Configuration ✅ PLANNED

**Status:** Feature plan complete. 4 tasks created, ready for implementation.
**Feature ID:** FEAT-D2AD
**Review:** TASK-REV-69BD (completed, score 85/100)

```bash
/feature-plan "NATS Server Configuration: nats-server.conf with JetStream enabled for DGX Spark GB10" \
  --context docs/design/specs/nats-infrastructure-system-spec.md
```

Covers: `config/nats-server.conf` — JetStream enabled, 1GB memory / 10GB file limits,
Tailscale-accessible on all interfaces, monitoring on port 8222, logging config.

**Key Decision:** Option 1 selected — single nats-server.conf with include accounts +
`envsubst` for credential management. NATS config does not natively support env var
interpolation, so `scripts/docker-entrypoint.sh` runs `envsubst` before launching
`nats-server`. Rejected: nsc Operator Model (overkill for single server, complexity 7/10),
auth tokens only (violates ADR-002).

**Tasks:**

| Wave | Task | Title | Complexity | Mode |
|------|------|-------|-----------|------|
| 1 | TASK-NATS-001 | Create nats-server.conf with JetStream | 3 | task-work |
| 2 | TASK-NATS-002 | Create account configs + envsubst entrypoint | 4 | task-work |
| 3 | TASK-NATS-003 | Create .env.example | 2 | direct |
| 4 | TASK-NATS-004 | Verify NATS startup + JetStream | 3 | task-work |

**Files:** `tasks/backlog/nats-server-config/` (4 task files + IMPLEMENTATION-GUIDE.md + README.md)
**AutoBuild:** `.guardkit/features/FEAT-D2AD.yaml`

**Next:** `/task-work TASK-NATS-001` or `/feature-build FEAT-D2AD`

### Feature 2 — Account-Based Multi-Tenancy

```bash
/feature-plan "Account-Based Multi-Tenancy: NATS accounts for APPMILLA and FINPROXY with scoped permissions" \
  --context docs/design/specs/nats-infrastructure-system-spec.md \
  --context docs/design/decisions/ADR-002-account-multi-tenancy.md
```

Covers: `config/accounts/appmilla.conf`, `config/accounts/finproxy.conf` — Rich + James
full access, Mark scoped to `finproxy.>` only, SYS admin account. `.env.example` with
password placeholders. Verification tests for isolation.
Tasks: TASK-5 through TASK-9.

### Feature 3 — JetStream Stream Definitions

```bash
/feature-plan "JetStream Stream Definitions: PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM streams" \
  --context docs/design/specs/nats-infrastructure-system-spec.md
```

Covers: `streams/stream-definitions.json`, `streams/provision-streams.sh` — 6 streams
with appropriate retention (WorkQueue vs Limits), max age, max messages. Project-scoped
stream creation for new clients. Idempotent provisioning.
Tasks: TASK-10 through TASK-14.

### Feature 4 — Docker Compose Deployment

```bash
/feature-plan "Docker Compose Deployment: NATS server with JetStream, volume persistence, health checks" \
  --context docs/design/specs/nats-infrastructure-system-spec.md
```

Covers: `docker-compose.yml` — NATS server container, JetStream volume mount,
health check, `ships-computer` Docker network, `.env.example`, restart policy.
Tasks: TASK-15 through TASK-19.

---

## Phase 2: Operations (Features 5-6)

### Feature 5 — Operations Scripts

```bash
/feature-plan "Operations Scripts: setup-gb10.sh, health-check.sh, backup-jetstream.sh" \
  --context docs/design/specs/nats-infrastructure-system-spec.md
```

Covers: `scripts/setup-gb10.sh` (one-shot GB10 deployment — NATS CLI install,
compose up, stream provision), `scripts/health-check.sh` (server info, stream list,
client count), `scripts/backup-jetstream.sh` (rsync to Synology NAS).
Tasks: TASK-20 through TASK-23.

### Feature 6 — KV Stores for Agent State

```bash
/feature-plan "KV Stores: agent-status, agent-registry, pipeline-state, jarvis-session buckets" \
  --context docs/design/specs/nats-infrastructure-system-spec.md \
  --context docs/design/decisions/ADR-002-account-multi-tenancy.md
```

Covers: KV bucket creation added to `provision-streams.sh`. 4 buckets: `agent-status`
(persistent), `agent-registry` (persistent — fleet routing table for CAN bus pattern),
`pipeline-state` (7d TTL), `jarvis-session` (1h TTL). KV watch test.
Tasks: TASK-24 through TASK-28.

---

## Phase 3: Fleet Compose (Feature 7)

This feature depends on agent containers existing — it defines the compose files
that bring the fleet online. Build this after at least one agent (e.g., Jarvis router
or General Purpose Agent) has a working Dockerfile.

### Feature 7 — Agent Fleet Compose

```bash
/feature-plan "Agent Fleet Compose: docker-compose.fleet.yml for containerised agent fleet with scaling" \
  --context docs/design/specs/nats-infrastructure-system-spec.md
```

Covers: `compose/docker-compose.fleet.yml` (all agent services extending base),
`compose/docker-compose.adapters.yml` (Telegram, Reachy, etc.), scaling pattern
(`--scale guardkitfactory=2`), container lifecycle → NATS registration mapping,
`scripts/fleet-status.sh` (show registered agents), `fleet.env.example`.
Tasks: TASK-29 through TASK-36.

**Note:** Feature 7 tasks are partially deferred — the compose file can be created
with placeholder images, but actual agent images don't exist until those agents are
built (Phases 3-8 in the fleet master index). Start with the Jarvis router image.

---

## Build Order (Dependency Chain)

```
Feature 1 (Server Config)     ← foundation
Feature 4 (Docker Compose)    ← depends on Feature 1 (mounts config)
Feature 2 (Accounts)          ← depends on Feature 1 (included by server config)
Feature 3 (Streams)           ← depends on Feature 4 (needs running NATS)
Feature 5 (Ops Scripts)       ← depends on Features 1-4 (orchestrates them)
Feature 6 (KV Stores)         ← depends on Feature 3 (added to provision script)
Feature 7 (Fleet Compose)     ← depends on Features 1-6 + agent container images
```

### Suggested Session Sequence

**Session 1:** Features 1 + 4 + 2 (server config + compose + accounts)
— End state: `docker compose up` starts NATS with JetStream and accounts

**Session 2:** Features 3 + 6 (streams + KV stores)
— End state: `provision-streams.sh` creates all streams and KV buckets

**Session 3:** Feature 5 (ops scripts)
— End state: `setup-gb10.sh` does full deployment from scratch

**Session 4:** Feature 7 (fleet compose) — when agent images are available
— End state: `docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml up`

---

## Key Files Produced

```
nats-infrastructure/
├── docker-compose.yml                    ← Feature 4 (NATS server, always on)
├── compose/
│   ├── docker-compose.fleet.yml          ← Feature 7 (agent fleet)
│   └── docker-compose.adapters.yml       ← Feature 7 (adapters)
├── config/
│   ├── nats-server.conf                  ← Feature 1 (TASK-NATS-001)
│   └── accounts/
│       └── accounts.conf.template        ← Feature 1 (TASK-NATS-002, envsubst template)
├── streams/
│   ├── provision-streams.sh              ← Features 3 + 6
│   └── stream-definitions.json           ← Feature 3
├── scripts/
│   ├── docker-entrypoint.sh              ← Feature 1 (TASK-NATS-002, envsubst + exec nats-server)
│   ├── verify-nats.sh                    ← Feature 1 (TASK-NATS-004, startup verification)
│   ├── setup-gb10.sh                     ← Feature 5
│   ├── health-check.sh                   ← Feature 5
│   ├── backup-jetstream.sh               ← Feature 5
│   └── fleet-status.sh                   ← Feature 7
├── .env.example                          ← Features 2 + 4
├── fleet.env.example                     ← Feature 7
├── docs/
│   ├── buildplan.md                      ← THIS FILE
│   └── design/
│       ├── specs/nats-infrastructure-system-spec.md
│       └── decisions/ADR-001..002
└── README.md
```

---

## Graphiti Knowledge Graph

**Config:** `.guardkit/graphiti.yaml` — LLM on GB10 vLLM (`neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`),
embeddings on GB10 vLLM (`nomic-embed-text-v1.5`), FalkorDB on Synology NAS (`whitestocks:6379`).

**Note:** Config was temporarily pointed at MacBook Ollama while the agentic dataset factory
used the GB10 GPU for GCSE study tutor training data generation. Switched back to GB10 vLLM
on 2026-04-07.

**Seeded episodes (2026-04-07):**

| Episode | Type | Nodes | Edges |
|---------|------|-------|-------|
| Project overview | project_overview | 19 | 24 |
| FEAT-D2AD review findings | full_doc | 10 | 8 |
| ADR-001 (standalone infra repo) | adr | 6 | 6 |
| ADR-002 (account multi-tenancy) | adr | 6 | 3 |

**CLI usage:** `OPENAI_API_KEY="not-needed-for-vllm" guardkit graphiti add-context <path> --type <type> --timeout 300`

---

## Validation

After each feature:

```bash
# Feature 1+4: NATS starts with JetStream
docker compose up -d
curl -sf http://localhost:8222/healthz    # health check
curl -sf http://localhost:8222/varz | jq '{server_name, version, jetstream}'

# Feature 2: Account isolation
nats pub test.msg "hello" --user rich --password $RICH_NATS_PASSWORD  # should work
nats pub finproxy.test "hello" --user mark --password $MARK_NATS_PASSWORD  # should work
nats pub pipeline.test "hello" --user mark --password $MARK_NATS_PASSWORD  # should FAIL

# Feature 3: Streams exist
nats stream ls

# Feature 6: KV buckets exist
nats kv ls

# Feature 5: Full setup
docker compose down -v
./scripts/setup-gb10.sh
./scripts/health-check.sh

# Feature 7: Fleet starts
docker compose -f docker-compose.yml -f compose/docker-compose.fleet.yml up -d
./scripts/fleet-status.sh
```

---

## Relationship to nats-core

nats-infrastructure provides the running NATS server.
nats-core provides the Python library that all agents use to communicate.

**Integration test:** After both are built, run nats-core's integration tests
(`pytest -m integration`) against the nats-infrastructure docker compose:

```bash
# Terminal 1: Start NATS
cd ~/Projects/appmilla_github/nats-infrastructure
docker compose up -d

# Terminal 2: Run nats-core integration tests
cd ~/Projects/appmilla_github/nats-core
NATS_URL=nats://localhost:4222 pytest -m integration
```
