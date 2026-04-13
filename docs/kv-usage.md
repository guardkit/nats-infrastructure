# KV Store Usage Patterns

This document describes the JetStream KV buckets used by the Jarvis Ship's Computer
fleet, including configuration details, CLI usage, and agent interaction patterns.

All KV buckets belong to the **APPMILLA** account (fleet-wide infrastructure) and are
provisioned by `streams/provision-streams.sh` from the definitions in
`streams/stream-definitions.json`.

---

## Bucket Reference

| Bucket | Key Pattern | TTL | Storage | History | Max Value | Purpose |
|--------|-------------|-----|---------|---------|-----------|---------|
| `agent-status` | `{agent_id}` | None (persistent) | file | 1 | 64KB | Last known status per agent — replaces polling |
| `agent-registry` | `{agent_id}` | None (persistent) | file | 5 | 256KB | Fleet routing table — capability manifests for Jarvis routing |
| `pipeline-state` | `{feature_id}` | 7 days | file | 3 | 64KB | Current pipeline state per feature |
| `jarvis-session` | `{session_id}` | 1 hour | memory | 1 | 128KB | Jarvis conversation session context |

### Configuration Rationale

- **`agent-status`** — History depth 1: only the latest status matters (online, offline,
  busy). No TTL because agent status should persist until the agent explicitly clears it
  or a fleet manager removes stale entries. File-backed for persistence across restarts.

- **`agent-registry`** — History depth 5: allows rollback if a broken capability manifest
  is pushed. Jarvis can fall back to a previous version. No TTL because registered agents
  should remain in the routing table until explicitly deregistered. File-backed for
  durability.

- **`pipeline-state`** — History depth 3: enables viewing recent state transitions (e.g.
  `planning` -> `implementing` -> `testing`). 7-day TTL auto-cleans completed or
  abandoned pipelines. File-backed for persistence across restarts.

- **`jarvis-session`** — History depth 1: only the current session context matters.
  Memory-backed for high write throughput (session context updates on every turn).
  1-hour TTL auto-cleans abandoned sessions without manual intervention.

---

## CLI Operations

### Put a Value

```bash
# Set agent status
nats kv put agent-status jarvis-router \
  '{"status":"online","pid":12345,"started_at":"2026-04-13T10:00:00Z"}'

# Register an agent
nats kv put agent-registry guardkitfactory \
  '{"agent_id":"guardkitfactory","capabilities":["feature-build","task-work"],"status":"available","queue_depth":0,"registered_at":"2026-04-13T10:00:00Z"}'

# Set pipeline state
nats kv put pipeline-state FEAT-7B86 \
  '{"feature_id":"FEAT-7B86","state":"implementing","wave":1,"updated_at":"2026-04-13T10:05:00Z"}'

# Set Jarvis session context
nats kv put jarvis-session sess-abc123 \
  '{"session_id":"sess-abc123","user":"rich","intent":"build-feature","context":{"feature_id":"FEAT-7B86"},"updated_at":"2026-04-13T10:10:00Z"}'
```

### Get a Value

```bash
# Get current status of a specific agent
nats kv get agent-status jarvis-router

# Get an agent's capability manifest
nats kv get agent-registry guardkitfactory

# Get current pipeline state for a feature
nats kv get pipeline-state FEAT-7B86

# Get Jarvis session context
nats kv get jarvis-session sess-abc123
```

Example output:

```
agent-status > jarvis-router created @ 13 Apr 26 10:00 UTC

{"status":"online","pid":12345,"started_at":"2026-04-13T10:00:00Z"}
```

### Delete a Key

```bash
# Remove agent status (e.g. agent decommissioned)
nats kv del agent-status jarvis-router

# Deregister an agent from the fleet
nats kv del agent-registry guardkitfactory

# Clear pipeline state (e.g. feature abandoned)
nats kv del pipeline-state FEAT-7B86

# End a Jarvis session explicitly
nats kv del jarvis-session sess-abc123
```

### List All Keys in a Bucket

```bash
nats kv ls agent-status
nats kv ls agent-registry
nats kv ls pipeline-state
nats kv ls jarvis-session
```

### View Bucket Info

```bash
# Show bucket configuration and stats
nats kv info agent-status
```

Example output:

```
Information for Key-Value Store Bucket agent-status created 2026-04-13 10:00:00

         Bucket Name: agent-status
        History Kept: 1
       Values Stored: 3
  Backing Store Name: KV_agent-status
  Backing Store Size: 1.2 KiB
    Maximum Value Size: 65536
```

### View Key History

```bash
# View revision history for a key (useful for agent-registry with history=5)
nats kv history agent-registry guardkitfactory
```

Example output:

```
agent-registry > guardkitfactory revision: 3 created @ 13 Apr 26 10:05 UTC
{"agent_id":"guardkitfactory","capabilities":["feature-build","task-work","review"],"status":"available","queue_depth":0,"registered_at":"2026-04-13T10:05:00Z"}

agent-registry > guardkitfactory revision: 2 created @ 13 Apr 26 10:02 UTC
{"agent_id":"guardkitfactory","capabilities":["feature-build","task-work"],"status":"available","queue_depth":0,"registered_at":"2026-04-13T10:02:00Z"}

agent-registry > guardkitfactory revision: 1 created @ 13 Apr 26 10:00 UTC
{"agent_id":"guardkitfactory","capabilities":["feature-build"],"status":"available","queue_depth":0,"registered_at":"2026-04-13T10:00:00Z"}
```

---

## Watch Pattern

The `nats kv watch` command subscribes to real-time change notifications on a KV bucket.
It blocks and prints each change as it occurs — new puts, updates, and deletes. This is
the recommended way for dashboards and routers to react to state changes without polling.

### Watch All Keys in a Bucket

```bash
nats kv watch agent-status
```

### Watch a Specific Key

```bash
nats kv watch agent-status jarvis-router
```

### Example Watch Output

Running `nats kv watch agent-status` in one terminal, while another terminal puts values:

```
[2026-04-13 10:00:01] PUT agent-status > jarvis-router: {"status":"online","pid":12345,"started_at":"2026-04-13T10:00:00Z"}
[2026-04-13 10:00:05] PUT agent-status > guardkitfactory: {"status":"online","pid":12346,"started_at":"2026-04-13T10:00:05Z"}
[2026-04-13 10:01:00] PUT agent-status > jarvis-router: {"status":"busy","pid":12345,"started_at":"2026-04-13T10:00:00Z"}
[2026-04-13 10:05:00] DEL agent-status > guardkitfactory
```

Each line shows the operation (`PUT` or `DEL`), the bucket, the key, and the value.
The watcher receives the current values of all existing keys on startup (initial state),
then streams subsequent changes. This means a newly started dashboard immediately gets
the full current state without a separate "list all" call.

---

## Agent Interaction Patterns

### 1. agent-status: Online/Offline Heartbeat

**Writer:** Each agent on startup and at regular heartbeat intervals
**Reader:** Dashboard watches for real-time fleet status display

```
Agent                        KV: agent-status              Dashboard
  |                                  |                         |
  |-- PUT jarvis-router ------------>|                         |
  |   {"status":"online",...}        |--- watch notification ->|
  |                                  |                         |
  |   (every 30s heartbeat)         |                         |
  |-- PUT jarvis-router ------------>|                         |
  |   {"status":"online",...}        |--- watch notification ->|
  |                                  |                         |
  |   (agent shutting down)          |                         |
  |-- PUT jarvis-router ------------>|                         |
  |   {"status":"offline",...}       |--- watch notification ->|
  |                                  |                         |
```

**Key format:** `{agent_id}` (e.g. `jarvis-router`, `guardkitfactory`, `finproxy-adapter`)

**Value schema:**
```json
{
  "status": "online",
  "pid": 12345,
  "started_at": "2026-04-13T10:00:00Z",
  "last_heartbeat": "2026-04-13T10:05:00Z"
}
```

**Status values:** `online`, `offline`, `busy`, `draining`

**Lifecycle:**
1. Agent starts -> puts `{"status":"online",...}`
2. Agent heartbeats every 30s -> puts `{"status":"online",...}` (refreshes timestamp)
3. Agent shutting down -> puts `{"status":"offline",...}`
4. Dashboard watches `agent-status` -> receives all changes in real time

### 2. agent-registry: Capability Manifests

**Writer:** Each agent on registration and when capabilities change
**Reader:** Jarvis router watches for routing table updates

```
Agent                        KV: agent-registry            Jarvis Router
  |                                  |                         |
  |-- PUT guardkitfactory ---------->|                         |
  |   {"capabilities":[...]}         |--- watch notification ->|
  |                                  |       (updates routing  |
  |                                  |        table in memory) |
  |   (capabilities updated)         |                         |
  |-- PUT guardkitfactory ---------->|                         |
  |   {"capabilities":[...,"review"]}|--- watch notification ->|
  |                                  |       (re-routes tasks) |
  |                                  |                         |
  |   (agent deregistering)          |                         |
  |-- DEL guardkitfactory ---------->|                         |
  |                                  |--- watch notification ->|
  |                                  |       (removes from     |
  |                                  |        routing table)   |
```

**Key format:** `{agent_id}` (e.g. `guardkitfactory`, `jarvis-router`)

**Value schema (capability manifest):**
```json
{
  "agent_id": "guardkitfactory",
  "capabilities": ["feature-build", "task-work"],
  "status": "available",
  "queue_depth": 0,
  "max_concurrent": 3,
  "registered_at": "2026-04-13T10:00:00Z"
}
```

**History depth 5** means Jarvis can inspect previous manifests if a bad update is pushed:
```bash
# View last 5 manifest versions
nats kv history agent-registry guardkitfactory
```

**Lifecycle:**
1. Agent starts -> puts capability manifest
2. Jarvis watches `agent-registry` -> builds/updates in-memory routing table
3. Agent capabilities change -> puts updated manifest -> Jarvis re-routes
4. Agent deregisters -> deletes key -> Jarvis removes from routing table

### 3. pipeline-state: Feature Pipeline Tracking

**Writer:** Pipeline service on each state transition
**Reader:** Dashboard reads current state; CLI queries for status

```
Pipeline Service             KV: pipeline-state            Dashboard / CLI
  |                                  |                         |
  |-- PUT FEAT-7B86 --------------->|                         |
  |   {"state":"planning",...}       |                         |
  |                                  |<-- GET FEAT-7B86 ------|
  |                                  |--- {"state":"planning"} |
  |                                  |                         |
  |-- PUT FEAT-7B86 --------------->|                         |
  |   {"state":"implementing",...}   |                         |
  |                                  |<-- GET FEAT-7B86 ------|
  |                                  |--- {"state":"impl..."} -|
  |                                  |                         |
  |   (7 days later, TTL expires)    |                         |
  |   key auto-deleted               |                         |
```

**Key format:** `{feature_id}` (e.g. `FEAT-7B86`, `FEAT-D2AD`)

**Value schema:**
```json
{
  "feature_id": "FEAT-7B86",
  "state": "implementing",
  "wave": 1,
  "total_waves": 3,
  "tasks_completed": 2,
  "tasks_total": 5,
  "updated_at": "2026-04-13T10:05:00Z"
}
```

**State values:** `planning`, `implementing`, `testing`, `reviewing`, `complete`, `failed`

**History depth 3** enables viewing recent state transitions:
```bash
# See the last 3 state transitions for a feature
nats kv history pipeline-state FEAT-7B86
```

**Lifecycle:**
1. Feature starts -> pipeline service puts `{"state":"planning",...}`
2. Each state transition -> pipeline service puts updated state
3. Dashboard/CLI reads current state via `nats kv get`
4. Feature completes or is abandoned -> key auto-expires after 7 days

### 4. jarvis-session: Conversation Context

**Writer:** Jarvis router on each conversation turn
**Reader:** Jarvis router reads on session resume

```
Jarvis Router                KV: jarvis-session
  |                                  |
  |-- PUT sess-abc123 ------------->|
  |   {"intent":"build-feature",...} |
  |                                  |
  |   (user sends follow-up)         |
  |-- GET sess-abc123 ------------->|
  |<-- {"intent":"build-feature",...}|
  |   (resumes context)              |
  |                                  |
  |-- PUT sess-abc123 ------------->|
  |   {"intent":"build-feature",     |
  |    "context":{...updated...}}    |
  |                                  |
  |   (1 hour idle, TTL expires)     |
  |   key auto-deleted               |
```

**Key format:** `{session_id}` (e.g. `sess-abc123`)

**Value schema:**
```json
{
  "session_id": "sess-abc123",
  "user": "rich",
  "intent": "build-feature",
  "context": {
    "feature_id": "FEAT-7B86",
    "current_task": "TASK-KV-004",
    "turn": 3
  },
  "created_at": "2026-04-13T10:00:00Z",
  "updated_at": "2026-04-13T10:10:00Z"
}
```

**Memory-backed storage** means this bucket does not survive NATS server restarts. This
is intentional — session context is ephemeral and can be rebuilt from conversation history.

**Lifecycle:**
1. New conversation -> Jarvis puts session context
2. Each turn -> Jarvis reads session context, processes, puts updated context
3. Session idle for 1 hour -> key auto-expires (TTL)
4. User returns after expiry -> Jarvis creates new session

---

## Provisioning

KV buckets are defined in `streams/stream-definitions.json` under the `kv_buckets` array
and provisioned by `streams/provision-streams.sh`.

```bash
# Provision all streams and KV buckets (idempotent)
./streams/provision-streams.sh

# Preview changes without applying
./streams/provision-streams.sh --dry-run

# Use a custom NATS URL
NATS_URL=nats://nats:4222 ./streams/provision-streams.sh
```

See [README.md](../README.md) for full provisioning documentation.

---

## Troubleshooting

### Check if a Bucket Exists

```bash
nats kv info agent-status
```

If the bucket does not exist, you'll see an error. Run the provisioning script to create it.

### List All KV Buckets

```bash
nats kv ls
```

### Purge All Keys in a Bucket (Caution)

```bash
# Remove all keys but keep the bucket
nats kv purge agent-status
```

### Delete a Bucket Entirely (Caution)

```bash
# Remove the bucket and all data — re-run provisioning to recreate
nats kv rm agent-status
```

### Key Not Found

If `nats kv get` returns "key not found", either:
- The key was never set (agent hasn't started yet)
- The key's TTL expired (check bucket TTL in the reference table above)
- The key was explicitly deleted

### Memory Bucket Lost After Restart

The `jarvis-session` bucket uses memory storage and **will not survive** a NATS server
restart. This is by design. After a restart, agents should re-establish sessions.
File-backed buckets (`agent-status`, `agent-registry`, `pipeline-state`) persist across
restarts.
