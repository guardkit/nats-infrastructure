---
id: TASK-REV-6E84
title: Review pipeline-state KV bucket decision (validate Option A, regression analysis)
status: completed
task_type: review
decision_required: true
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
completed: 2026-04-16T00:00:00Z
completed_location: tasks/completed/TASK-REV-6E84/
organized_files:
  - TASK-REV-6E84.md
  - review-report.md
priority: medium
tags: [nats-infrastructure, kv-store, review, regression-analysis, pipeline-state, architecture-review]
complexity: 4
related_tasks: [TASK-PSKV-001]
source_document: forge/docs/research/forge-build-plan-alignment-review.md
review_results:
  mode: decision
  depth: standard
  score: 90
  findings_count: 5
  recommendations_count: 1
  decision: proceed_option_b_keep_bucket
  regression_risk: low
  report_path: tasks/completed/TASK-REV-6E84/review-report.md
  completed_at: 2026-04-16T00:00:00Z
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  note: "Decision/review task — no code changes, no tests required"
---

# Task: Review pipeline-state KV bucket decision (validate Option A)

## Description

TASK-PSKV-001 proposes three options for the `pipeline-state` NATS KV bucket and recommends **Option A** (delete the bucket entirely, consolidate on SQLite as the single durable store for Forge state). This review task performs an independent analysis to validate that recommendation — checking for regressions, dependency risks, and alignment with the broader architecture before the decision is acted upon.

## Context

### Origin

The `forge-build-plan-alignment-review.md` (TASK-REV-A1F2, §2.2 correction 6) identified a conflict:

- **ADR-SP-013** says: "JetStream owns the queue; SQLite (`~/.forge/forge.db`) owns the history."
- `streams/stream-definitions.json:92–96` and `kv/kv-definitions.json` define a `pipeline-state` NATS KV bucket with description "Current pipeline state per feature_id".
- **ADR-SP-017** (proposed, v2.2) explicitly defers this question to TASK-PSKV-001.

Today there are three potential stores for Forge runtime state: JetStream (queue), SQLite (history), and `pipeline-state` KV (purpose unclear). The anchor documents two.

### Current KV bucket configuration (`kv/kv-definitions.json`)

```json
{
  "name": "pipeline-state",
  "ttl": "7d",
  "storage": "file",
  "history": 3,
  "max_value_size": "64KB",
  "replicas": 1,
  "description": "Current pipeline state per feature_id"
}
```

### TASK-PSKV-001 options summary

| Option | Approach | Recommendation |
|--------|----------|----------------|
| **A** | Delete KV bucket entirely; SQLite is single durable store | **Recommended** |
| **B** | Keep KV for live cross-process visibility; SQLite for history | Fallback |
| **C** | Move runtime state to KV; SQLite as archive only | Overkill for now |

## Review scope

This review must validate the following before Option A can be accepted:

### 1. Regression analysis — files and tests referencing `pipeline-state`

Identify every file in `nats-infrastructure` that references the `pipeline-state` bucket and assess the impact of its removal:

- `kv/kv-definitions.json` — bucket definition (line 22-29)
- `streams/stream-definitions.json` — any KV bucket provisioning references
- `scripts/setup-gb10.sh` or `provision-streams.sh` — provisioning scripts
- `tests/test_kv_definitions.py` — test assertions on bucket existence
- `tests/test_kv_watch_integration.py` — KV watch integration tests
- `docs/kv-usage.md` — documentation references
- `README.md` — any mentions
- `.guardkit/` — autobuild artefacts referencing the bucket

**Question**: Can the bucket be removed without breaking any existing tests or scripts?

### 2. Cross-repo dependency analysis

Check whether any sibling repos depend on or reference `pipeline-state`:

- **forge** — does any code, doc, or config assume `pipeline-state` KV exists?
- **jarvis** — does the vision doc reference watching `pipeline-state` for live Forge status?
- **specialist-agent** — any references?
- **nats-core** — any KV client code that targets `pipeline-state`?

**Question**: Are there consumers outside `nats-infrastructure` that would break?

### 3. Architecture alignment validation

- Does Option A align with ADR-SP-013 ("JetStream owns the queue; SQLite owns the history")?
- Does Option A conflict with any v2.2 anchor additions proposed in the alignment review?
- Is the "two-store model" (JetStream + SQLite) sufficient for all Forge state-machine needs (IDLE → PREPARING → RUNNING → FINALISING/PAUSED → COMPLETE/FAILED)?
- Can `forge status` work without KV when running on the same host as the Forge?

### 4. Future-proofing assessment

- If multi-machine visibility becomes a real requirement later, how hard is it to add the KV bucket back?
- Is Option A genuinely reversible without architectural rework?
- Does the "revisit when dashboard/Jarvis needs live state" escape hatch hold up?

### 5. Deliverable validation

If Option A is confirmed, the following changes are required in `nats-infrastructure`:

- [ ] Remove `pipeline-state` from `kv/kv-definitions.json`
- [ ] Update `streams/stream-definitions.json` if it references the bucket
- [ ] Update provisioning scripts (`setup-gb10.sh`, etc.)
- [ ] Update or remove KV watch tests that target `pipeline-state`
- [ ] Update `docs/kv-usage.md` and `README.md`
- [ ] Record decision as ADR (ADR-SP-018 or amendment to ADR-SP-013)

**Question**: Is this list complete? Are there additional files or scripts that need updating?

## Acceptance criteria

- [ ] All files referencing `pipeline-state` in `nats-infrastructure` identified and impact assessed
- [ ] Cross-repo dependencies checked (forge, jarvis, specialist-agent, nats-core)
- [ ] Option A validated or challenged against ADR-SP-013 and v2.2 anchor
- [ ] Regression risk rated (none / low / medium / high) with justification
- [ ] Reversibility of Option A confirmed or flagged
- [ ] Complete list of files requiring changes if Option A proceeds
- [ ] Clear recommendation: proceed with Option A, switch to Option B, or request more information

## Out of scope

- Implementing the deletion (that is TASK-PSKV-001's deliverable after this review approves the direction)
- Writing Forge code that reads/writes SQLite or KV
- Cross-machine visibility features (dashboards, remote `forge status`)
- Changes to sibling repos (forge, jarvis, specialist-agent, nats-core)
