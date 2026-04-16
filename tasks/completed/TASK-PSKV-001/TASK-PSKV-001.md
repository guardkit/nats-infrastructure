---
id: TASK-PSKV-001
title: Decide fate of pipeline-state NATS KV bucket (consolidate with SQLite or keep as runtime state)
status: completed
task_type: review
decision_required: true
parent_review: forge/TASK-REV-A1F2
related_tasks: [TASK-REV-6E84]
priority: medium
tags: [nats-infrastructure, kv-store, decision, storage, forge-v2.2]
complexity: 3
completed: 2026-04-16T00:00:00Z
completed_location: tasks/completed/TASK-PSKV-001/
organized_files:
  - TASK-PSKV-001.md
decision:
  outcome: option_b_keep_bucket
  rationale: "Forge is JetStream-native and specialist-agent is deploying imminently; deleting the KV bucket now would require re-provisioning days later. Decision finalised by TASK-REV-6E84 independent review (score 90/100, regression risk: low)."
  overrode_original_recommendation: true
  original_recommendation: option_a_delete_bucket
  decided_by: TASK-REV-6E84
  decided_at: 2026-04-16T00:00:00Z
deliverables_status:
  infrastructure_changes: not_required
  infrastructure_changes_note: "Option B = keep bucket as-is. No edits to streams/, kv/, scripts/, or README needed."
  adr_in_forge_repo: deferred_to_forge
  adr_note: "ADR-SP-018 (or amendment to ADR-SP-013) must be written in forge/docs/research/forge-pipeline-architecture.md — out of scope for nats-infrastructure."
  graphiti_architecture_decisions: captured
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  note: "Decision task — no code changes, no tests required"
---

# Task: Decide fate of `pipeline-state` NATS KV bucket

## Why this is a review task

TASK-REV-A1F2 (forge alignment review) §2.2 surfaced a conflict:

- Anchor **ADR-SP-013** says: "JetStream owns the queue; SQLite (`~/.forge/forge.db`) owns the history. The Forge writes to SQLite at each state transition."
- `streams/stream-definitions.json:92–96` defines a `pipeline-state` NATS KV bucket with the description "Forge pipeline state".
- **ADR-SP-017** (proposed, v2.2) explicitly notes: "This ADR does **not** resolve the `pipeline-state` NATS KV bucket question (it competes with SQLite for runtime Forge state) — that needs its own ADR once Rich has decided, tracked as TASK-PSKV-001 in nats-infrastructure."

Today there are three *potential* stores for Forge runtime state: JetStream (queue), SQLite (history), and `pipeline-state` KV (purpose unclear). The anchor documents two. Rich needs to pick one of three paths.

## Options

### Option A — Delete the `pipeline-state` KV bucket entirely

Consolidate on SQLite for all runtime and historical state. The KV bucket is removed from `stream-definitions.json` and `provision-streams.sh`. SQLite remains the single durable store for Forge state (ADR-SP-013 stands unchanged).

- **Pro:** simplest. Two stores (JetStream + SQLite) match the anchor exactly. One place to look when debugging. No risk of drift between SQLite and KV.
- **Con:** SQLite is on the Forge host only. Other machines (Rich's MacBook running a dashboard, Jarvis on GB10) cannot read live Forge state without either an API or shipping SQLite replicas. For a single-host factory today this is fine; for multi-machine visibility it is a limitation.

### Option B — Keep `pipeline-state` KV as live cross-process visibility; SQLite remains history

The KV bucket holds the *current* state of the running build (current stage, coach score, PAUSED status, INTERRUPTED flag). Forge writes to both KV and SQLite at each state transition. Other processes (dashboards, Jarvis, a second `forge status` CLI invocation on another machine) read from KV for live state.

- **Pro:** solves cross-process visibility without inventing a new API. Jarvis can stream live progress to adapters by watching the KV key for a given `feature_id`. `forge status` on a second machine works.
- **Con:** two stores to keep in sync. Drift risk. Must document clearly what lives where (KV = current running/paused state only; SQLite = everything else including completed/failed history). Anchor ADR-SP-013 needs amendment.

### Option C — Move runtime state entirely to `pipeline-state` KV; SQLite becomes the long-term archive only

The Forge writes running state (PREPARING/RUNNING/PAUSED/FINALISING) to KV. On completion/failure, it flushes final state to SQLite and clears the KV key. SQLite is append-only history.

- **Pro:** clean separation — KV is ephemeral runtime, SQLite is immutable history. No drift because there is no overlap window.
- **Con:** rewrite of the Forge state-machine persistence layer (which does not yet exist, so the cost is only in design). Crash recovery becomes more complex (crash with live KV state plus an unacked JetStream message needs a three-way reconciliation). Anchor ADR-SP-013 needs material rewrite.

## Recommendation

**Option A** is the right default for a single-developer factory in its first year. Delete the KV bucket, keep SQLite as the single durable store, confirm ADR-SP-013 stands. Revisit if multi-machine live visibility becomes a real requirement (e.g. when Rich wants a dashboard running on his MacBook while the Forge runs on GB10).

**Option B** is the fallback if Rich wants dashboard/Jarvis live visibility *now*. Accept the drift risk in exchange for live cross-process reads.

**Option C** is overkill for current requirements.

## Deliverable

One ADR written into `forge/docs/research/forge-pipeline-architecture.md` §9 (new ADR-SP-018 or amendment to ADR-SP-013), plus:

- If Option A: delete `pipeline-state` bucket from `streams/stream-definitions.json`, update provisioning script, update README
- If Option B: document in `forge-pipeline-architecture.md` §5/§6 what lives in KV vs SQLite; amend ADR-SP-013; keep the KV bucket as-is
- If Option C: full redesign of the Forge state-machine persistence, much larger follow-up task in the forge repo

## Acceptance criteria

- [ ] Decision made and recorded as an ADR in `forge/docs/research/forge-pipeline-architecture.md`
- [ ] Infrastructure changes (delete KV or keep KV) applied to `streams/stream-definitions.json` and `provision-streams.sh`
- [ ] README updated to reflect the final set of KV buckets
- [ ] Forge build plan prerequisites updated if the decision changes them
- [ ] Graphiti episode added to `nats-infrastructure` `architecture_decisions` group recording the decision

## Out of scope

- Implementing any Forge code that reads/writes these stores
- Cross-machine visibility features (dashboards, remote `forge status`) — those follow from the decision, not precede it
