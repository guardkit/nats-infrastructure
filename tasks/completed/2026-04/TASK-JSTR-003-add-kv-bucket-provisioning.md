---
id: TASK-JSTR-003
title: Add KV bucket provisioning to provision-streams.sh
task_type: feature
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 3
dependencies:
- TASK-JSTR-002
status: completed
priority: normal
tags:
- jetstream
- kv
- provisioning
estimated_minutes: 30
consumer_context:
- task: TASK-JSTR-001
  consumes: stream-definitions.json
  framework: jq + nats CLI
  driver: jq
  format_note: 'JSON array at .kv_buckets[] with fields: name, ttl, description'
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7044
  base_branch: main
  started_at: '2026-04-13T22:16:16.664694'
  last_updated: '2026-04-13T22:30:50.449839'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:16:16.664694'
    player_summary: 'Added 4 KV buckets to stream-definitions.json with correct TTL
      values per system spec. Extended provision-streams.sh with provision_kv_bucket()
      function that uses nats kv add/info/update commands with idempotent check-then-create-or-update
      pattern. KV buckets are provisioned after streams. TTL is conditionally applied
      only for non-null values. Added separate summary counters (kv_created, kv_updated,
      kv_current, kv_errors) and combined summary output. Added comprehensive test
      coverage: 23 new tes'
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-7044** is `status: completed`; deliverables shipped on `main` (pointer commit `8f0dce0`). No code changed by this sweep.

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
