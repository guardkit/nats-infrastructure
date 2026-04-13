---
id: TASK-JSTR-004
title: "Create validation tests for stream definitions and provisioning"
task_type: testing
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-JSTR-001, TASK-JSTR-002]
status: pending
priority: high
tags: [testing, validation, streams, shellcheck]
estimated_minutes: 45
---

# Task: Create validation tests

## Description

Create pytest tests that validate stream definitions and the provisioning script without requiring a running NATS server. Follow the existing test pattern in `tests/test_nats_server_conf.py`.

## Test Scope

### 1. JSON Schema Validation (`tests/test_stream_definitions.py`)

- `stream-definitions.json` is valid JSON
- All required fields present for each stream (name, subjects, retention, max_age, max_msgs, storage, replicas)
- All 6 core streams from the spec are defined (PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM)
- FINPROXY project-scoped stream is defined
- Retention values are valid (`work` or `limits`)
- Max age values use valid NATS duration format (e.g., `7d`, `24h`, `1h`)
- No duplicate stream names
- All core subjects follow dot-separated hierarchical naming

### 2. Spec Compliance (`tests/test_stream_definitions.py`)

- PIPELINE retention is `work` (WorkQueue) per spec
- AGENTS max_age is `24h` per spec
- JARVIS max_msgs is `1000` per spec
- All streams have `replicas: 1` (single server)
- All streams have `storage: file`

### 3. Script Validation (`tests/test_provision_streams.py`)

- `provision-streams.sh` exists and is executable
- Script passes `shellcheck` (if available)
- Script contains required components: NATS_URL variable, jq dependency check, health check wait

## Acceptance Criteria

- [ ] `tests/test_stream_definitions.py` validates JSON structure and spec compliance
- [ ] `tests/test_provision_streams.py` validates script exists and passes shellcheck
- [ ] All tests pass with `pytest tests/ -v`
- [ ] Tests follow existing pattern: no running NATS server required
- [ ] Test names follow convention: `test_<subject>_<scenario>_<expected>`

## Implementation Notes

- Use `json.load()` for JSON parsing tests
- Use `subprocess.run(["shellcheck", ...])` for shell validation (skip if shellcheck not installed)
- Reference `tests/test_nats_server_conf.py` for the established test pattern
