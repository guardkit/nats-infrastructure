---
id: TASK-JSTR-006
title: "Document stream operations in README"
task_type: documentation
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 1
dependencies: [TASK-JSTR-002]
status: pending
priority: low
tags: [documentation, readme, streams]
estimated_minutes: 15
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
