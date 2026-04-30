---
id: TASK-FCH-001
title: "Canonical NATS provisioning for forge (FEAT-FORGE-008 Phase 4+)"
status: in_progress
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T12:00:00Z
previous_state: backlog
tags: [forge, handoff, canonical-provisioning, jetstream, kv, feat-forge-008]
task_type: implementation
complexity: 5
parent_handoff: ../../forge/docs/handoffs/F8-007a-nats-canonical-provisioning.md
parent_review: ../../forge/tasks/backlog/TASK-REV-F008-fix-feat-forge-008-validation-failures.md
test_results:
  status: n/a
  coverage: null
  last_run: null
  note: "Audit-only task — no executable code path. AC-1/AC-4/AC-5 verified by static comparison against handoff doc; AC-2/AC-3 awaiting user decision; AC-6 deferred."
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

- [x] **AC-1** — Confirm anchor v2.1 reconciliation for FLEET / JARVIS /
      NOTIFICATIONS retention values matches the floors enumerated in
      the handoff doc §3 (PIPELINE / AGENTS-COMMAND / AGENTS-RESULT /
      FLEET / JARVIS / NOTIFICATIONS).
      **Verified (2026-04-30):** all forge-pinned floors met by
      `streams/stream-definitions.json`. JARVIS retention vs. v2.1
      anchor flagged as a separate documentation hygiene follow-up
      (see "Audit findings" §AC-1) — non-blocking for forge.
- [x] **AC-2** — Confirm the GB10 deployment target — docker-compose
      (already in this repo) vs. a future systemd unit on the bare host.
      Update `nats-infrastructure/scripts/setup-gb10.sh` if the choice
      changes.
      **Decision (Rich, 2026-04-30):** docker-compose stays. No edit
      to `setup-gb10.sh` required.
- [x] **AC-3** — Decide whether a dedicated `forge` service-identity user
      lands before the FEAT-FORGE-008 Phase 6.4 canonical-freeze
      walkthrough, or whether the shared APPMILLA `rich`/`james` account
      is used for sign-off (handoff doc §6 lists both options).
      **Decision (Rich, 2026-04-30):** stay on shared APPMILLA
      `rich`/`james` for Phase 6.4 sign-off. No edit to
      `accounts.conf.template` required.
- [x] **AC-4** — Provision the KV buckets the handoff doc §5 enumerates:
      `agent-registry`, `agent-status`, `pipeline-state`. Cross-check
      against existing `kv/kv-definitions.json`.
      **Verified (2026-04-30):** all three buckets declared with floors
      met. `kv/provision-kv.sh` runs them at GB10 setup time.
- [x] **AC-5** — Confirm `scripts/verify-nats.sh` covers the health
      probes the handoff doc §7 lists (`/healthz`, `/varz`, `/jsz`,
      `nats stream info PIPELINE`).
      **Verified (2026-04-30):** all four probes covered (Checks 1, 2,
      3, 5 in `verify-nats.sh`).
- [x] **AC-6** — Notify forge (via a comment / PR / message) once
      provisioning is live on the canonical NATS target so
      `forge` can re-run RUNBOOK-FEAT-FORGE-008-validation Phases 4–6
      and formally declare Step 6 canonical.
      **Notified (2026-04-30):**
      [`forge/docs/handoffs/F8-007a-status-update-canonical-nats-live.md`](../../../forge/docs/handoffs/F8-007a-status-update-canonical-nats-live.md).
      Provisioning is live on `promaxgb10-41b1:4222` — full evidence
      (verify-nats.sh PASS, live stream config matching §3.3 floors,
      KV inventory) captured in the status-update doc.

## Audit findings — 2026-04-30

Static audit only (no live NATS instance touched). Each finding cites the
file + line(s) that satisfy or block the AC.

### AC-1 — Stream floor reconciliation: ✅ floors met (anchor follow-up flagged)

`streams/stream-definitions.json` matches every floor enumerated in the
handoff doc §3.3 exactly:

| Stream         | Floor (subjects / retention / max_age / max_msgs / storage) | Actual                                       | Status |
|----------------|-------------------------------------------------------------|----------------------------------------------|--------|
| `PIPELINE`     | `pipeline.>` / `work` / 7d / 10000 / `file`                 | `pipeline.>` / `work` / 7d / 10000 / `file`  | ✅      |
| `AGENTS`       | `agents.>` / `limits` / 24h / 5000 / `file`                 | `agents.>` / `limits` / 24h / 5000 / `file`  | ✅      |
| `FLEET`        | `fleet.>` / `limits` / 1h / 5000 / `file`                   | `fleet.>` / `limits` / 1h / 5000 / `file`    | ✅      |
| `NOTIFICATIONS`| `notifications.>` / `work` / 24h / 1000 / `file`            | `notifications.>` / `work` / 24h / 1000 / `file` | ✅  |
| `FINPROXY`     | `finproxy.>` / `work` / 24h / 5000 / `file`                 | `finproxy.>` / `work` / 24h / 5000 / `file`  | ✅      |

The handoff doc itself confirms in §3.3: *"The set already declared in
nats-infrastructure/streams/stream-definitions.json is acceptable for
forge."* No edits to `stream-definitions.json` are required to satisfy
forge.

`JARVIS` (`limits` / 1h / 1000) and `SYSTEM` (`limits` / 1h / 500) are
not pinned by forge — handoff §3.3 explicitly says *"forge does not pin
those retention values."*

🟡 **Anchor follow-up (non-blocking for forge):** the handoff doc
references *"the v2.1 anchor"* as the upstream topology source-of-truth
for `FLEET` / `JARVIS` / `NOTIFICATIONS` retention. A grep of
`nats-core/docs/` and `nats-infrastructure/docs/` did not surface a
canonical document that names itself "v2.1 anchor" with retention
values. This is a documentation hygiene gap, not a forge blocker — the
forge floors are independently met. Action: when the anchor doc is
landed (or located), cross-reference the JARVIS retention value
specifically (currently `limits` / 1h / 1000 / `file`).

### AC-4 — KV bucket reconciliation: ✅ floors met

`kv/kv-definitions.json` matches every floor enumerated in the handoff
doc §5 exactly:

| Bucket           | Floor (TTL / history / storage) | Actual                  | Status |
|------------------|----------------------------------|-------------------------|--------|
| `agent-registry` | none (∞) / ≥ 5 / `file`          | `""` (∞) / 5 / `file`   | ✅      |
| `agent-status`   | none (∞) / ≥ 1 / `file`          | `""` (∞) / 1 / `file`   | ✅      |
| `pipeline-state` | ≥ 7d / ≥ 3 / `file`              | `7d` / 3 / `file`       | ✅      |

`jarvis-session` (`1h` / 1 / `memory`) is in the file but is **not**
required by forge — handoff §5 explicitly excludes it.

The handoff doc itself confirms in §5: *"the set already declared in
nats-infrastructure/kv/kv-definitions.json satisfies this floor."* No
edits to `kv-definitions.json` are required.

### AC-5 — Health probe coverage in `verify-nats.sh`: ✅ all handoff §7 probes covered

| Handoff §7 probe                          | `verify-nats.sh` location          | Status |
|-------------------------------------------|-------------------------------------|--------|
| `GET /healthz` → 200                      | Check 1, lines 127–136              | ✅      |
| `GET /varz` → JSON `server_name`+`version`| Check 3, lines 169–195              | ✅      |
| `GET /jsz` → JSON `memory`+`store`        | Check 2, lines 141–164              | ✅      |
| `nats stream info PIPELINE` → exit 0      | Check 5, lines 268–294 (PIPELINE in `EXPECTED_STREAMS`) | ✅ |

The script also covers the FEAT-FORGE-008 sibling streams (AGENTS,
JARVIS, NOTIFICATIONS, SYSTEM, FLEET, FINPROXY) and includes a
placeholder-credentials regression guard (Check 4b) that is independent
of the handoff but supports the same Phase 4–6 evidence capture. No
changes required.

### AC-2 — GB10 deployment target: ✅ docker-compose (Rich, 2026-04-30)

Current state: `docker-compose.yml` + `scripts/setup-gb10.sh` (one-shot
build → up → provision → verify) ship as the canonical path. There is
no systemd unit in the repo. The compose service has
`restart: unless-stopped`, a `wget`-based healthcheck, and a named
volume `nats-data` for JetStream durability — i.e. the operational
properties a systemd unit would provide are already in place via
docker-compose.

Open question per handoff §9.2 — pick one and stick with it:

**Decision (Rich, 2026-04-30): docker-compose.** No edits to
`scripts/setup-gb10.sh`, `docker-compose.yml`, or `Dockerfile` required.
The runbook prose on the forge side (RUNBOOK-FEAT-FORGE-008-validation
§0.6) should be settled to docker-compose; this gets communicated to
forge in the AC-6 notification.

### AC-3 — Forge service-identity user: ✅ shared `rich`/`james` (Rich, 2026-04-30)

Current state: `config/accounts/accounts.conf.template` defines
APPMILLA with `rich` and `james` users at full `publish: ">"` /
`subscribe: ">"`. This satisfies forge's runtime needs as-is — handoff
§6: *"that is sufficient."*

Open question per handoff §9.3 — does Phase 6.4 canonical-freeze sign
off against:

**Decision (Rich, 2026-04-30): shared `rich` / `james` for Phase 6.4
canonical-freeze sign-off.** No edit to
`config/accounts/accounts.conf.template`. The dedicated `forge` user
(handoff §6.1/6.2/6.3 ACL) remains a future hardening option but is
explicitly out of scope for this task.

Phase 6.4 evidence on the forge side should cite the shared APPMILLA
account; this gets communicated to forge in the AC-6 notification.

### AC-6 — Notify forge: ✅ live and notified (2026-04-30)

**Live verification (2026-04-30, on `promaxgb10-41b1`):**

- `docker compose up -d` — `ships-computer-nats` container created and
  reached healthy status (~4s).
- `streams/provision-streams.sh` — 7 streams created (PIPELINE, AGENTS,
  JARVIS, NOTIFICATIONS, SYSTEM, FLEET, FINPROXY), 4 KV buckets created
  (agent-status, agent-registry, pipeline-state, jarvis-session), 0
  errors.
- `scripts/verify-nats.sh` — **7 passed, 0 failed** (handoff §7 probes:
  `/healthz`=200, `/jsz` initialised, `/varz` server_name=ships-computer
  version 2.11.16, all 7 streams found, APPMILLA + FINPROXY auth pass,
  placeholder credentials rejected).
- Live `nats stream info` per stream confirms the forge-pinned floors
  (PIPELINE / AGENTS / FLEET / NOTIFICATIONS / FINPROXY) match handoff
  §3.3 exactly. NATS reports `work` retention as `workqueue` in the
  live API — equivalent.

**Notification artefact:**
[`forge/docs/handoffs/F8-007a-status-update-canonical-nats-live.md`](../../../forge/docs/handoffs/F8-007a-status-update-canonical-nats-live.md)
is a sibling status-update doc to the original handoff spec. It records
the AC-2/AC-3 decisions, full verification evidence, the connection
URL forge should target (`nats://promaxgb10-41b1:4222` over Tailscale,
or `nats://localhost:4222` from the GB10 host), and the JARVIS-anchor
documentation hygiene follow-up. Forge can act on this immediately —
re-run RUNBOOK Phases 4–6 and capture §6.4 canonical-freeze evidence.

### All ACs complete — task ready to close

Pending forge-side acknowledgement of the status-update doc, this task
can move to `completed/`. No remaining `nats-infrastructure` work
unless forge reports a regression during their RUNBOOK Phase 4–6
re-run.

### Follow-ups (not blocking task closure)

- **JARVIS retention vs. v2.1 anchor:** locate or write the canonical
  v2.1 anchor doc and cross-reference JARVIS retention. Currently
  `limits` / 1h / 1000 / `file`. Documentation hygiene only — does not
  affect forge.
- **Future hardening (deferred per AC-3):** dedicated `forge` service
  identity with the §6.1/6.2/6.3 ACL. Open a separate task if/when
  hardening requirements change.

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
