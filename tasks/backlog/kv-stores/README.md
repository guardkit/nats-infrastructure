# KV Stores Feature

**Feature ID**: FEAT-KV
**Review**: TASK-REV-4721
**Status**: Planned
**Complexity**: 4/10

## Problem

The agent fleet needs lightweight key-value state storage for:
- Agent online/offline status (replaces polling)
- Fleet routing table (capability manifests for Jarvis)
- Pipeline state machines (per feature_id)
- Jarvis conversation session context

NATS JetStream KV provides this natively without additional infrastructure.

## Solution

Add 4 KV buckets to the NATS infrastructure, provisioned via a new
`kv/provision-kv.sh` script that mirrors the established `streams/provision-streams.sh`
pattern. Declarative definitions live in `kv/kv-definitions.json`.

## Tasks

| # | Task | Complexity | Wave |
|---|------|-----------|------|
| TASK-KV-001 | Create kv-definitions.json | 2 | 1 |
| TASK-KV-002 | Create provision-kv.sh | 4 | 2 |
| TASK-KV-003 | Update setup-gb10.sh | 2 | 2 |
| TASK-KV-004 | Document KV usage patterns | 2 | 1 |
| TASK-KV-005 | Test KV watch scenarios | 3 | 3 |

## Files Created/Modified

- `kv/kv-definitions.json` (new)
- `kv/provision-kv.sh` (new)
- `scripts/setup-gb10.sh` (modified)
- `README.md` or `docs/kv-usage.md` (modified/new)
- `tests/test-kv-provisioning.sh` (new)
