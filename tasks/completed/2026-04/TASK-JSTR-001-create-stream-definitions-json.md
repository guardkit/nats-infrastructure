---
id: TASK-JSTR-001
title: Create stream-definitions.json with all 7 streams
task_type: declarative
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: completed
priority: high
tags:
- jetstream
- streams
- json
estimated_minutes: 30
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7044
  base_branch: main
  started_at: '2026-04-13T22:01:59.760325'
  last_updated: '2026-04-13T22:07:46.510861'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:01:59.760325'
    player_summary: 'Created streams/stream-definitions.json with all 7 JetStream
      stream definitions (6 core + 1 project-scoped FINPROXY). Each stream includes
      all required fields: name, subjects, retention, max_age, max_msgs, storage,
      replicas, plus metadata fields scope and description. Retention values use NATS
      CLI format (''work'' for WorkQueue, ''limits'' for Limits). All values match
      the system spec exactly. FINPROXY uses reasonable defaults of 24h max_age and
      5000 max_msgs as specified. Comprehensive test suite w'
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-7044** is `status: completed`; deliverables shipped on `main` (pointer commit `8f0dce0`). No code changed by this sweep.

# Task: Create stream-definitions.json

## Description

Create `streams/stream-definitions.json` with declarative definitions for all 7 JetStream streams (6 core + 1 project-scoped). This file is the single source of truth for stream configuration, consumed by `provision-streams.sh`.

## Context

From the system spec (Feature 3), the streams are:

| Stream | Subjects | Retention | Max Age | Max Messages | Scope |
|--------|----------|-----------|---------|-------------|-------|
| PIPELINE | `pipeline.>` | WorkQueue | 7 days | 10,000 | core |
| AGENTS | `agents.>` | Limits | 24 hours | 5,000 | core |
| JARVIS | `jarvis.>` | Limits | 1 hour | 1,000 | core |
| NOTIFICATIONS | `notifications.>` | WorkQueue | 24 hours | 1,000 | core |
| SYSTEM | `system.>` | Limits | 1 hour | 500 | core |
| FLEET | `fleet.>` | Limits | 1 hour | 5,000 | core |
| FINPROXY | `finproxy.>` | WorkQueue | 24 hours | 5,000 | project |

All streams use `file` storage, `replicas: 1` (single server).

## JSON Structure

Each stream object maps directly to `nats stream add/update` CLI flags:

```json
{
  "streams": [
    {
      "name": "PIPELINE",
      "subjects": ["pipeline.>"],
      "retention": "work",
      "max_age": "7d",
      "max_msgs": 10000,
      "storage": "file",
      "replicas": 1,
      "scope": "core",
      "description": "Dev pipeline events"
    }
  ]
}
```

## Acceptance Criteria

- [ ] File created at `streams/stream-definitions.json`
- [ ] All 6 core streams defined with exact spec values
- [ ] FINPROXY project stream included with `"scope": "project"` and reasonable defaults (24h, 5000)
- [ ] All required fields present: name, subjects, retention, max_age, max_msgs, storage, replicas
- [ ] JSON is valid (parseable by `jq`)
- [ ] Retention values use NATS CLI format: `work` (WorkQueue) or `limits` (Limits)

## Implementation Notes

- The spec does not specify max_age or max_msgs for FINPROXY. Use 24h and 5000 as reasonable defaults.
- The `scope` field is metadata for tooling/documentation, not consumed by NATS CLI.
- Consider adding an optional `account` field for FINPROXY to support per-account provisioning.
