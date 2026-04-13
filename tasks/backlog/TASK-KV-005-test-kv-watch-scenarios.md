---
id: TASK-KV-005
title: "Test KV watch - agent-status and agent-registry scenarios"
task_type: testing
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 3
implementation_mode: direct
complexity: 3
dependencies:
  - TASK-KV-002
status: pending
estimated_minutes: 30
---

# Task: Test KV watch - agent-status and agent-registry scenarios

## Description

Create integration test scripts that verify KV bucket provisioning and watch
functionality against a running NATS server. These are shell-based integration
tests (not pytest) since this is an infrastructure repo.

## Acceptance Criteria

- [ ] Test script verifies all 4 KV buckets are created by provision-kv.sh
- [ ] Test: put a value to agent-status, get it back, verify content
- [ ] Test: watch agent-status in background, put a value, verify watch receives update
- [ ] Test: put a value to agent-registry, verify history depth (put 6 values, verify only 5 retained)
- [ ] Test: put a value to jarvis-session, verify it expires after TTL (1hr — can use shorter TTL for test)
- [ ] Test: put a value to pipeline-state, verify it persists across broker restart
- [ ] Test: provision-kv.sh --dry-run produces expected output without creating buckets
- [ ] All tests pass against Docker Compose NATS instance

## Implementation Notes

Create `tests/test-kv-provisioning.sh` as a bash test script:

```bash
#!/usr/bin/env bash
# Test KV bucket provisioning and operations
set -euo pipefail

PASS=0
FAIL=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "[PASS] $desc"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $desc (expected: $expected, got: $actual)"
        FAIL=$((FAIL + 1))
    fi
}

# Test 1: Verify buckets exist
# Test 2: Put/get round-trip
# Test 3: Watch receives updates
# Test 4: History depth enforcement
# Test 5: Dry-run mode
# Summary
```

Requires Docker Compose NATS to be running.
