# Feature: JetStream Stream Definitions

**Feature ID**: FEAT-JSTR | **Review**: TASK-REV-E14C | **Status**: Planned

## Problem

The NATS infrastructure needs 6 core JetStream streams (PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM), 1 project-scoped stream (FINPROXY), and 4 KV buckets provisioned in a repeatable, idempotent way. Stream definitions must be declarative and version-controlled. The provisioning process must be safe to re-run after reboots or definition changes.

## Solution

A declarative `stream-definitions.json` file as the single source of truth, consumed by an idempotent `provision-streams.sh` script that uses the `nats` CLI via `jq` to check-then-create-or-update each stream.

## Key Decisions

- **JSON + Shell** over inline scripts, server config, or Terraform
- **Check-then-create-or-update** idempotency over error suppression or journal-based migrations
- **Single JSON file** for all streams (core + project) with `scope` field

## Tasks (6)

| Wave | Task | Type | Complexity | Description |
|------|------|------|-----------|-------------|
| 1 | TASK-JSTR-001 | declarative | 2 | Create stream-definitions.json |
| 2 | TASK-JSTR-002 | feature | 5 | Create provision-streams.sh (idempotent) |
| 3 | TASK-JSTR-003 | feature | 3 | Add KV bucket provisioning |
| 3 | TASK-JSTR-004 | testing | 4 | Create validation tests |
| 3 | TASK-JSTR-005 | feature | 2 | Integration with setup/verify scripts |
| 3 | TASK-JSTR-006 | documentation | 1 | Document stream operations |

## Getting Started

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for execution strategy and diagrams.

```bash
# Start with Wave 1
/task-work TASK-JSTR-001

# Then Wave 2
/task-work TASK-JSTR-002

# Wave 3 tasks can run in parallel
/task-work TASK-JSTR-003
/task-work TASK-JSTR-004
```
