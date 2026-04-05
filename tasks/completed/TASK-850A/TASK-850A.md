---
id: TASK-850A
title: Merge fleet compose addendum into parent spec
status: completed
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
completed: 2026-04-04T00:00:00Z
priority: normal
tags: [documentation, spec-merge, fleet, compose]
complexity: 4
task_type: documentation
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Merge fleet compose addendum into parent spec

## Description

Read both specification files and merge the addendum content into the parent spec following the explicit merge instructions in the addendum:

- **Parent**: `docs/design/specs/nats-infrastructure-system-spec.md`
- **Addendum**: `docs/design/specs/nats-infrastructure-spec-addendum-fleet-compose.md`

## Acceptance Criteria

### Feature 3 (Stream Definitions) Updates
- [x] Add FLEET stream to the stream definitions table:
  - Stream: FLEET, Subjects: `fleet.>`, Retention: Limits, Max Age: 1 hour, Max Messages: 5,000, Purpose: Agent registration, deregistration, heartbeats
- [x] Add corresponding `nats stream add FLEET` command to the `provision-streams.sh` example

### Feature 6 (KV Stores) Updates
- [x] Add `agent-registry` KV bucket to the KV Buckets table:
  - Bucket: agent-registry, Purpose: Fleet routing table — agent capability manifests, updated on register/deregister. Jarvis reads this for routing. Survives Jarvis restarts. TTL: None (persistent)
- [x] Add TASK-27 and TASK-28 to the Feature 6 tasks

### Feature 7 (Agent Fleet Compose) — New Section
- [x] Add Feature 7: Agent Fleet Compose as a new section after Feature 6 and before Non-Functional Requirements
- [x] Include the revised containerisation decision
- [x] Include the two-file compose architecture
- [x] Include the `docker-compose.fleet.yml` definition with all agent services
- [x] Include the scaling pattern
- [x] Include the agent container lifecycle → NATS registration flow
- [x] Include TASK-29 through TASK-36

### Repository Structure Updates
- [x] Add `compose/` directory with `docker-compose.fleet.yml` and `docker-compose.adapters.yml`
- [x] Add `fleet-status.sh` to `scripts/`

### Post-Merge Verification
- [x] Task numbering is continuous (TASK-1 through TASK-36)
- [x] Document reads as one coherent spec
- [x] Delete the addendum file `nats-infrastructure-spec-addendum-fleet-compose.md`

## Test Requirements
- [x] Verify all 36 tasks are present and continuously numbered
- [x] Verify FLEET stream appears in Feature 3 table
- [x] Verify agent-registry bucket appears in Feature 6 table
- [x] Verify Feature 7 section exists between Feature 6 and Non-Functional Requirements
- [x] Verify repository structure includes new compose/ and scripts/ entries
- [x] Verify addendum file is deleted

## Implementation Notes

Follow the merge instructions at the top of the addendum file precisely. Do not rewrite or reinterpret — transplant content as specified.
