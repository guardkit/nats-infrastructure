---
complexity: 5
consumer_context:
- consumes: stream-definitions.json
  driver: jq
  format_note: 'JSON array at .streams[] with fields: name, subjects, retention, max_age,
    max_msgs, storage, replicas'
  framework: jq + nats CLI
  task: TASK-JSTR-001
dependencies:
- TASK-JSTR-001
estimated_minutes: 60
feature_id: FEAT-JSTR
id: TASK-JSTR-002
implementation_mode: task-work
parent_review: TASK-REV-E14C
priority: high
status: design_approved
tags:
- jetstream
- provisioning
- idempotency
- shell
task_type: feature
title: Create provision-streams.sh with idempotent check/create/update
wave: 2
---

# Task: Create provision-streams.sh with idempotent provisioning

## Description

Create `streams/provision-streams.sh` that reads `stream-definitions.json` via `jq`, loops through stream definitions, and applies the check-then-create-or-update idempotency pattern. The script must be safe to run multiple times -- on first deploy, on reboot, and after stream definition changes.

## Idempotency Pattern

For each stream in JSON:
1. Check if stream exists: `nats stream info $NAME --json 2>/dev/null`
2. If not exists: `nats stream add $NAME ... --defaults` -> log `[CREATE]`
3. If exists: `nats stream update $NAME ... --force` -> log `[UPDATE]`
4. On error: log `[ERROR]` and continue to next stream (do not abort)

## Requirements

- Read stream definitions from `streams/stream-definitions.json`
- Support `NATS_URL` env var (default: `nats://localhost:4222`)
- Support `NATS_CREDS` env var for optional credentials
- Support `--dry-run` flag for safe preview (shows what would happen without acting)
- Log every action with prefixed format: `[CREATE] PIPELINE`, `[UPDATE] AGENTS`, `[OK] FLEET`
- Use `set -euo pipefail` for strict error handling
- Handle update failures gracefully (log and continue to next stream)
- Wait for NATS health before attempting provisioning (health check loop)
- Print summary at end: `N created, M updated, K already current, E errors`

## Acceptance Criteria

- [ ] Script reads all streams from `stream-definitions.json`
- [ ] First run creates all 7 streams successfully
- [ ] Second run detects existing streams and reports `[OK]` or `[UPDATE]` (no errors)
- [ ] Changing a value in JSON (e.g., max_age) propagates on next run via `[UPDATE]`
- [ ] `--dry-run` flag shows planned actions without modifying anything
- [ ] Script exits 0 when all streams provisioned, non-zero only on fatal errors
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify stream-definitions.json contract from TASK-JSTR-001."""
import json
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("stream-definitions.json")
def test_stream_definitions_json_format():
    """Verify stream-definitions.json matches the expected format.

    Contract: JSON array at .streams[] with fields: name, subjects, retention, max_age, max_msgs, storage, replicas
    Producer: TASK-JSTR-001
    """
    with open("streams/stream-definitions.json") as f:
        data = json.load(f)

    assert "streams" in data, "Top-level 'streams' key must exist"
    assert len(data["streams"]) >= 7, f"Expected at least 7 streams, got {len(data['streams'])}"

    required_fields = {"name", "subjects", "retention", "max_age", "max_msgs", "storage", "replicas"}
    for stream in data["streams"]:
        missing = required_fields - set(stream.keys())
        assert not missing, f"Stream {stream.get('name', '?')} missing fields: {missing}"
        assert stream["retention"] in ("work", "limits"), f"Invalid retention: {stream['retention']}"
```

## Implementation Notes

- The `nats stream update --force` flag bypasses interactive confirmation
- `nats stream update` can modify most parameters but CANNOT change subject filters on a stream with data
- For the FINPROXY project-scoped stream, the script may need to use different credentials (account-scoped access). Handle via optional `account` field in JSON.
- `jq` is required; include a check at script start: `command -v jq >/dev/null || { echo "jq required"; exit 1; }`