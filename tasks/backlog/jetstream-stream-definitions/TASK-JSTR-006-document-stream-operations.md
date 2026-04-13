---
id: TASK-JSTR-006
title: Document stream operations in README
task_type: documentation
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 1
dependencies:
- TASK-JSTR-002
status: in_review
priority: low
tags:
- documentation
- readme
- streams
estimated_minutes: 15
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7044
  base_branch: main
  started_at: '2026-04-13T22:16:16.668358'
  last_updated: '2026-04-13T22:26:36.058104'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:16:16.668358'
    player_summary: Added a comprehensive 'JetStream Streams' section to README.md
      documenting all 6 core streams and 1 project stream in tables, 4 KV buckets
      with TTL info, provisioning commands with environment variable options, idempotency
      guarantees with the check-then-create-or-update pattern, and a step-by-step
      guide for adding new project streams. Also updated documentation to reflect
      concurrent KV bucket additions to stream-definitions.json and provision-streams.sh
      (KV Buckets subsection, updated summary fo
    player_success: true
    coach_success: true
---

# Task: Document stream operations in README

## Description

Add a "JetStream Streams" section to README.md documenting how to run provisioning, add new project streams, verify streams, and the idempotency guarantees.

## Sections to Add

### JetStream Streams

- **Overview**: Brief description of the 6 core streams and their purpose
- **Provisioning**: How to run `provision-streams.sh` (first time and re-runs)
- **Dry Run**: How to preview changes with `--dry-run`
- **Adding a Project Stream**: How to add a new client stream (add entry to JSON, re-run script)
- **KV Buckets**: Brief description of the 4 KV buckets and their purpose
- **Idempotency**: Explanation that the script is safe to re-run and will update changed definitions
- **Verification**: How to check stream status with `verify-nats.sh` or `nats stream ls`

## Acceptance Criteria

- [ ] README.md has a "JetStream Streams" section
- [ ] All 6 core streams listed with purpose
- [ ] Provisioning commands documented
- [ ] Idempotency guarantees explained
- [ ] Project stream addition process documented
