# Implementation Guide: KV Stores

**Feature**: KV Stores — agent-status, agent-registry, pipeline-state, jarvis-session buckets
**Review**: TASK-REV-4721
**Approach**: Option 1 — Separate `kv/` directory with definitions JSON + provisioning script

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["Agent startup/heartbeat\n(put agent-status)"]
        W2["Agent register/deregister\n(put agent-registry)"]
        W3["Pipeline service\n(put pipeline-state)"]
        W4["Jarvis router\n(put jarvis-session)"]
    end

    subgraph Storage["KV Buckets (JetStream)"]
        S1[("agent-status\nfile, no TTL, history=1")]
        S2[("agent-registry\nfile, no TTL, history=5")]
        S3[("pipeline-state\nfile, TTL=7d, history=3")]
        S4[("jarvis-session\nmemory, TTL=1h, history=1")]
    end

    subgraph Reads["Read Paths"]
        R1["Dashboard\n(watch agent-status)"]
        R2["Jarvis router\n(watch agent-registry)"]
        R3["Dashboard / CLI\n(get pipeline-state)"]
        R4["Jarvis router\n(get jarvis-session)"]
    end

    W1 -->|"nats kv put"| S1
    W2 -->|"nats kv put"| S2
    W3 -->|"nats kv put"| S3
    W4 -->|"nats kv put"| S4

    S1 -->|"nats kv watch"| R1
    S2 -->|"nats kv watch"| R2
    S3 -->|"nats kv get"| R3
    S4 -->|"nats kv get"| R4
```

_All write paths have corresponding read paths. No disconnections._

---

## Task Dependencies

```mermaid
graph TD
    T1[TASK-KV-001: Create kv-definitions.json] --> T2[TASK-KV-002: Create provision-kv.sh]
    T2 --> T3[TASK-KV-003: Update setup-gb10.sh]
    T2 --> T5[TASK-KV-005: Test KV watch scenarios]
    T4[TASK-KV-004: Document KV usage patterns]

    style T1 fill:#cfc,stroke:#090
    style T4 fill:#cfc,stroke:#090
```

_Tasks with green background can run in parallel (Wave 1: TASK-KV-001 + TASK-KV-004)._

---

## Integration Contract: Provisioning Script reads Definitions

```mermaid
sequenceDiagram
    participant S as setup-gb10.sh
    participant P as provision-kv.sh
    participant D as kv-definitions.json
    participant N as NATS Server

    S->>P: Execute after stream provisioning
    P->>D: Read bucket definitions (jq)
    D-->>P: 4 bucket configs
    loop For each bucket
        P->>N: nats kv info BUCKET
        alt Bucket exists
            N-->>P: Bucket info (OK)
            P->>P: Log [OK] BUCKET
        else Bucket missing
            P->>N: nats kv add BUCKET --flags
            N-->>P: Created
            P->>P: Log [CREATE] BUCKET
        end
    end
    P-->>S: Exit 0 (summary)
```

---

## Section 4: Integration Contracts

### Contract: KV_DEFINITIONS_FILE
- **Producer task:** TASK-KV-001 (Create kv-definitions.json)
- **Consumer task(s):** TASK-KV-002 (Create provision-kv.sh)
- **Artifact type:** JSON file at `kv/kv-definitions.json`
- **Format constraint:** JSON object with `"kv_buckets"` array, each entry having: `name` (string), `ttl` (string, nats duration or empty), `storage` (string: "file"|"memory"), `history` (int), `max_value_size` (string, e.g. "64K"), `replicas` (int), `description` (string)
- **Validation method:** `jq '.kv_buckets | length' kv/kv-definitions.json` returns `4`

### Contract: PROVISION_KV_SCRIPT
- **Producer task:** TASK-KV-002 (Create provision-kv.sh)
- **Consumer task(s):** TASK-KV-003 (Update setup-gb10.sh)
- **Artifact type:** Executable shell script at `kv/provision-kv.sh`
- **Format constraint:** Script must accept `--dry-run` flag, use `NATS_URL` and `NATS_CREDS` env vars, exit 0 on success
- **Validation method:** `kv/provision-kv.sh --dry-run` exits 0 and outputs expected bucket names

---

## Execution Strategy

### Wave 1: Definitions + Documentation (parallel)

| Task | Mode | Description |
|------|------|-------------|
| TASK-KV-001 | direct | Create `kv/kv-definitions.json` |
| TASK-KV-004 | direct | Document KV usage patterns in README |

### Wave 2: Provisioning Script + Setup (sequential)

| Task | Mode | Description |
|------|------|-------------|
| TASK-KV-002 | task-work | Create `kv/provision-kv.sh` (depends on TASK-KV-001) |
| TASK-KV-003 | direct | Update `scripts/setup-gb10.sh` (depends on TASK-KV-002) |

### Wave 3: Testing

| Task | Mode | Description |
|------|------|-------------|
| TASK-KV-005 | direct | Test KV watch scenarios (depends on TASK-KV-002) |

---

## KV Bucket Configuration Reference

| Bucket | Keys Pattern | TTL | Storage | History | Max Value | Purpose |
|--------|-------------|-----|---------|---------|-----------|---------|
| `agent-status` | `{agent_id}` | None | file | 1 | 64KB | Agent online/offline/busy status |
| `agent-registry` | `{agent_id}` | None | file | 5 | 256KB | Capability manifests for routing |
| `pipeline-state` | `{feature_id}` | 7d | file | 3 | 64KB | Pipeline state machine |
| `jarvis-session` | `{session_id}` | 1h | memory | 1 | 128KB | Conversation context |

### Design Rationale

- **agent-registry history=5**: Allows rollback if a broken capability manifest is pushed. Jarvis can fall back to a previous version.
- **pipeline-state history=3**: Enables viewing recent state transitions (e.g., `planning` -> `implementing` -> `testing`).
- **jarvis-session memory storage**: Ephemeral data with high write frequency. Memory avoids disk I/O. 1hr TTL auto-cleans abandoned sessions.
- **agent-status history=1**: Only the latest status matters. No need to track status history.

### Account Scoping

All 4 KV buckets belong to the **APPMILLA** account (fleet-wide infrastructure). The FINPROXY account does not need access to these buckets. No additional account configuration is required per ADR-002.
