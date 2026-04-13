---
id: TASK-KV-004
title: "Document KV usage patterns in README"
task_type: documentation
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: pending
estimated_minutes: 30
---

# Task: Document KV usage patterns in README

## Description

Add a KV Stores section to the project README documenting:
1. What each KV bucket is for
2. How to use get/put/watch operations via `nats` CLI
3. How agents should interact with each bucket
4. TTL and history behaviour

## Acceptance Criteria

- [ ] README.md has a "KV Stores" section (or dedicated docs/kv-usage.md)
- [ ] Each bucket documented with purpose, TTL, storage type, history depth
- [ ] CLI examples for `nats kv get`, `nats kv put`, `nats kv watch`
- [ ] Agent interaction patterns documented:
  - agent-status: agent puts status on startup/heartbeat, dashboard watches
  - agent-registry: agent puts manifest on register, Jarvis watches for changes
  - pipeline-state: pipeline service puts state transitions, dashboard reads
  - jarvis-session: Jarvis puts session context, reads on resume
- [ ] Watch pattern explained with example output

## Implementation Notes

Use `nats` CLI examples that can be copy-pasted for testing:

```bash
# Put a value
nats kv put agent-status jarvis-router '{"status":"online","timestamp":"2026-04-13T10:00:00Z"}'

# Get a value
nats kv get agent-status jarvis-router

# Watch all changes
nats kv watch agent-status

# Watch specific key
nats kv watch agent-status jarvis-router
```

For agent-registry, document the capability manifest schema:
```json
{
  "agent_id": "guardkitfactory",
  "capabilities": ["feature-build", "task-work"],
  "status": "available",
  "queue_depth": 0,
  "registered_at": "2026-04-13T10:00:00Z"
}
```
