---
id: TASK-KV-003
title: "Update setup-gb10.sh to call KV provisioning"
task_type: feature
parent_review: TASK-REV-4721
feature_id: FEAT-KV
wave: 2
implementation_mode: direct
complexity: 2
dependencies:
  - TASK-KV-002
status: pending
estimated_minutes: 15
---

# Task: Update setup-gb10.sh to call KV provisioning

## Description

Update `scripts/setup-gb10.sh` (or the equivalent one-shot deployment script)
to call `kv/provision-kv.sh` after stream provisioning completes.

The setup sequence should be:
1. Start NATS via Docker Compose
2. Wait for health
3. Provision JetStream streams (`streams/provision-streams.sh`)
4. **Provision KV buckets (`kv/provision-kv.sh`)** <-- NEW
5. Verify

## Acceptance Criteria

- [ ] `scripts/setup-gb10.sh` calls `kv/provision-kv.sh` after stream provisioning
- [ ] KV provisioning runs only after NATS is healthy
- [ ] Script exits non-zero if KV provisioning fails fatally
- [ ] Verification step includes `nats kv ls` to confirm buckets exist
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

The setup script already has the pattern for calling provision-streams.sh.
Add the KV call in the same section, right after stream provisioning.

Also update `scripts/health-check.sh` to include KV bucket listing in its output.
