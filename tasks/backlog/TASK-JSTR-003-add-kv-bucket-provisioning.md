---
id: TASK-JSTR-003
title: "Add KV bucket provisioning to provision-streams.sh"
task_type: feature
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 3
dependencies: [TASK-JSTR-002]
status: pending
priority: normal
tags: [jetstream, kv, provisioning]
estimated_minutes: 30
consumer_context:
  - task: TASK-JSTR-001
    consumes: stream-definitions.json
    framework: "jq + nats CLI"
    driver: "jq"
    format_note: "JSON array at .kv_buckets[] with fields: name, ttl, description"
---

# Task: Add KV bucket provisioning

## Description

Extend `streams/stream-definitions.json` and `streams/provision-streams.sh` to also provision the 4 KV buckets from the system spec (Feature 6). Apply the same idempotency pattern: check-then-create-or-update.

## KV Buckets (from spec)

| Bucket | Purpose | TTL |
|--------|---------|-----|
| `agent-status` | Last known status per agent | None (persistent) |
| `agent-registry` | Fleet routing table -- agent capability manifests | None (persistent) |
| `pipeline-state` | Current pipeline state per feature_id | 7 days |
| `jarvis-session` | Jarvis conversation session context | 1 hour |

## JSON Extension

Add a `kv_buckets` array to `stream-definitions.json`:

```json
{
  "streams": [...],
  "kv_buckets": [
    {
      "name": "agent-status",
      "ttl": null,
      "description": "Last known status per agent"
    }
  ]
}
```

## Provisioning Pattern

- Use `nats kv info BUCKET` to check existence
- Use `nats kv add BUCKET` to create (with `--ttl` if specified)
- Use `nats kv update BUCKET` to update TTL on existing buckets
- Same `[CREATE]`/`[UPDATE]`/`[OK]` logging pattern

## Acceptance Criteria

- [ ] All 4 KV buckets defined in `stream-definitions.json`
- [ ] `provision-streams.sh` creates KV buckets after streams
- [ ] Idempotent: re-running does not error on existing buckets
- [ ] TTL values applied correctly (null = no TTL, persistent)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify kv_buckets section in stream-definitions.json."""
import json
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("stream-definitions.json")
def test_kv_buckets_json_format():
    """Verify kv_buckets matches the expected format.

    Contract: JSON array at .kv_buckets[] with fields: name, ttl, description
    Producer: TASK-JSTR-001
    """
    with open("streams/stream-definitions.json") as f:
        data = json.load(f)

    assert "kv_buckets" in data, "Top-level 'kv_buckets' key must exist"
    assert len(data["kv_buckets"]) >= 4, f"Expected at least 4 KV buckets, got {len(data['kv_buckets'])}"

    for bucket in data["kv_buckets"]:
        assert "name" in bucket, f"KV bucket missing 'name' field"
```
