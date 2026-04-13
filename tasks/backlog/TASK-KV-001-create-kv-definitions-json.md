---
id: TASK-KV-001
title: "Create kv-definitions.json with 4 bucket definitions"
task_type: declarative
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: pending
estimated_minutes: 20
---

# Task: Create kv-definitions.json with 4 bucket definitions

## Description

Create the declarative JSON definitions file for NATS JetStream KV buckets at
`kv/kv-definitions.json`. This mirrors the established pattern from
`streams/stream-definitions.json` (FEAT-7044).

Define 4 KV buckets:

| Bucket | TTL | Storage | History | Max Value Size |
|--------|-----|---------|---------|---------------|
| `agent-status` | None | file | 1 | 64KB |
| `agent-registry` | None | file | 5 | 256KB |
| `pipeline-state` | 7d | file | 3 | 64KB |
| `jarvis-session` | 1h | memory | 1 | 128KB |

## Acceptance Criteria

- [ ] `kv/kv-definitions.json` exists with valid JSON
- [ ] All 4 buckets defined with name, ttl, storage, history, max_value_size, description
- [ ] TTL values use nats CLI duration format (e.g. "7d", "1h", "" for none)
- [ ] Storage types correctly assigned (file for persistent, memory for ephemeral)
- [ ] History depth matches spec requirements
- [ ] JSON schema is consistent with stream-definitions.json style

## Implementation Notes

Reference `streams/stream-definitions.json` for style consistency.

KV bucket fields map to `nats kv add` CLI flags:
- `name` -> bucket name
- `ttl` -> `--ttl` (empty string = no TTL)
- `storage` -> `--storage` (file or memory)
- `history` -> `--history`
- `max_value_size` -> `--max-value-size`
- `replicas` -> `--replicas` (always 1 for single-node)
