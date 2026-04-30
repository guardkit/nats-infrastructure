---
id: TASK-FCH-001
title: "Canonical NATS provisioning for forge (FEAT-FORGE-008 Phase 4+)"
status: backlog
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
tags: [forge, handoff, canonical-provisioning, jetstream, kv, feat-forge-008]
task_type: implementation
complexity: 5
parent_handoff: ../../forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md
parent_review: ../../forge/tasks/backlog/TASK-REV-F008-fix-feat-forge-008-validation-failures.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Canonical NATS provisioning for forge (FEAT-FORGE-008 Phase 4+)

## Description

`forge` has published its canonical-provisioning handoff document at
[`forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md`](../../../forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md).
That document is the contract — it enumerates everything `forge`
publishes, consumes, and persists, with the floors (retention, max
bytes/messages, replicas, consumer ack policy, KV history depth) sourced
verbatim from the forge codebase.

This task tracks the `nats-infrastructure`-side delivery: provisioning
the streams, KV buckets, and (optionally) the dedicated `forge` service
identity that the handoff document specifies.

The handoff doc closing condition (forge-side TASK-F8-007a / AC-2 + AC-4)
is satisfied as soon as **this task file exists** — `forge`'s side of the
delegation is complete the moment the cross-repo tracking artefact
lands. `nats-infrastructure`'s actual provisioning delivery is tracked
by this task on its own timeline, independent of the FEAT-FORGE-008
review's closure.

## Acceptance Criteria

- [ ] **AC-1** — Confirm anchor v2.1 reconciliation for FLEET / JARVIS /
      NOTIFICATIONS retention values matches the floors enumerated in
      the handoff doc §3 (PIPELINE / AGENTS-COMMAND / AGENTS-RESULT /
      FLEET / JARVIS / NOTIFICATIONS).
- [ ] **AC-2** — Confirm the GB10 deployment target — docker-compose
      (already in this repo) vs. a future systemd unit on the bare host.
      Update `nats-infrastructure/scripts/setup-gb10.sh` if the choice
      changes.
- [ ] **AC-3** — Decide whether a dedicated `forge` service-identity user
      lands before the FEAT-FORGE-008 Phase 6.4 canonical-freeze
      walkthrough, or whether the shared APPMILLA `rich`/`james` account
      is used for sign-off (handoff doc §6 lists both options).
- [ ] **AC-4** — Provision the KV buckets the handoff doc §5 enumerates:
      `agent-registry`, `agent-status`, `pipeline-state`. Cross-check
      against existing `kv/kv-definitions.json`.
- [ ] **AC-5** — Confirm `scripts/verify-nats.sh` covers the health
      probes the handoff doc §7 lists (`/healthz`, `/varz`, `/jsz`,
      `nats stream info PIPELINE`).
- [ ] **AC-6** — Notify forge (via a comment / PR / message) once
      provisioning is live on the canonical NATS target so
      `forge` can re-run RUNBOOK-FEAT-FORGE-008-validation Phases 4–6
      and formally declare Step 6 canonical.

## Source-of-truth references

- Forge handoff doc (the contract):
  [`forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md`](../../../forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md)
- Forge parent review:
  [`forge/tasks/backlog/TASK-REV-F008-...md`](../../../forge/tasks/backlog/TASK-REV-F008-fix-feat-forge-008-validation-failures.md)
- Forge parent task (closes when this file is created):
  [`forge/tasks/completed/TASK-F8-007a/TASK-F8-007a-...md`](../../../forge/tasks/completed/TASK-F8-007a/TASK-F8-007a-nats-canonical-provisioning-handoff.md)

## Out of scope

- Implementing forge's NATS adapters (already shipped — see
  `forge/src/forge/adapters/nats/`).
- Re-running forge's FEAT-FORGE-008 validation runbook (forge-operator
  action once provisioning is live).
- The forge production Dockerfile (TASK-F8-007b → spawned
  FEAT-FORGE-009; see forge `tasks/completed/TASK-F8-007b/`).
