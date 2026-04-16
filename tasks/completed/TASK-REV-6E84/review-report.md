# Review Report: TASK-REV-6E84 (Final — Revision 2)

## Executive Summary

**Final recommendation: Option B — keep the `pipeline-state` KV bucket.**

Forge implementation is imminent (days, not months). Removing the bucket now to re-add it immediately is wasteful churn across 9 files. The bucket is pre-provisioned infrastructure waiting for its producer — that's readiness, not noise.

The architecture case for keeping it is strong:

- **nats-core** already defines typed pipeline events (BUILD_STARTED, BUILD_PROGRESS, BUILD_COMPLETE, BUILD_FAILED) that carry per-feature state — these are *event streams*, not KV state. KV state is complementary (current snapshot vs event history).
- **nats-core** already has KV abstractions (`NATSKVManifestRegistry` for `agent-registry`) — the pattern for a `pipeline-state` KV client already exists
- **specialist-agent** is about to deploy in product-owner and architect roles — real agents will be in the fleet soon
- No production code reads or writes `pipeline-state` KV today

The revised question is: **do JetStream pipeline events make the KV state bucket redundant, or complementary?**

**Answer: Complementary.** Events tell you *what happened*; KV state tells you *what is the state right now*. Both have value. With Forge implementation days away, the bucket should stay. The Forge orchestrator will be the natural producer — writing KV state at each pipeline transition alongside JetStream events.

**Decision: Keep the bucket. No changes to nats-infrastructure required.**

---

## Revision Context

The user provided three key updates:

1. **Forge design docs referencing SQLite are out of date** — Forge will use NATS JetStream interactions from the start, not SQLite as the primary state store
2. **nats-core and nats-infrastructure are implemented** — the infrastructure layer is real and shipping
3. **specialist-agent is about to begin integration testing** in product-owner and architect deployments

---

## Revised Finding 1: The JetStream-Native Forge Changes the Architecture

### What nats-core already provides

`nats-core` is a fully implemented shared library with:

| Component | What it provides | Relevance |
|-----------|-----------------|-----------|
| `Topics.Pipeline` | 6 typed pipeline topics (FEATURE_PLANNED → BUILD_COMPLETE/FAILED) | These are JetStream *events*, not KV *state* |
| Pipeline event schemas | `BuildStartedPayload`, `BuildProgressPayload`, `BuildCompletePayload`, `BuildFailedPayload` | Rich typed payloads with feature_id, build_id, wave progress, task counts |
| `NATSKVManifestRegistry` | KV-backed agent registry using `agent-registry` bucket | **Proves the pattern** — a `PipelineStateRegistry` using `pipeline-state` bucket would follow the same design |
| `MessageEnvelope` | Versioned, correlation-ID'd envelope for all events | Standard envelope pattern already in place |

### Events vs State — why both have value

| Aspect | JetStream Events (pipeline.build-progress.*) | KV State (pipeline-state) |
|--------|-----------------------------------------------|--------------------------|
| **Question answered** | "What happened?" | "What is happening right now?" |
| **Access pattern** | Subscribe to stream, replay history | GET by key, instant answer |
| **Retention** | 7 days in PIPELINE stream | Overwritten on each transition |
| **Consumer model** | Must be subscribed when events fire (or replay from stream) | Read anytime — current snapshot always available |
| **Use case** | Build logs, audit trail, event replay | Dashboard polling, agent queries, `forge status` |
| **Example** | "Feature X transitioned from RUNNING to FINALISING at 14:03" | "Feature X is currently FINALISING, wave 3/4, 78% complete" |

### Revised architecture alignment

With Forge going JetStream-native:

- **ADR-SP-013** ("JetStream owns the queue; SQLite owns the history") is itself out of date if Forge won't use SQLite
- The two-store model becomes: **JetStream (events + queue) + KV (current state snapshots)**
- This is actually a cleaner architecture than JetStream + SQLite — everything stays in NATS

**Important**: This doesn't mean `pipeline-state` KV is needed *today*. It means the architectural case for it is stronger than the original review assumed, and the path to needing it is shorter.

---

## Revised Finding 2: Cross-Repo Dependencies (Updated)

| Repo | Status | Pipeline Relevance |
|------|--------|-------------------|
| **nats-core** | Implemented, shipping | Defines `Topics.Pipeline.*` and `NATSKVManifestRegistry` — pattern for `pipeline-state` KV client exists |
| **nats-infrastructure** | Implemented, shipping | Provisions the bucket (currently unused by consumers) |
| **specialist-agent** | About to deploy (product-owner, architect) | Publishes fleet events, no pipeline subscriptions yet. Will need pipeline visibility when orchestrated by Forge |
| **forge** | Not yet implemented | Will be the primary *producer* of pipeline state. When built, will publish pipeline events and potentially write KV state |
| **jarvis** | Zero references | Future consumer — would watch KV for live Forge status to relay to adapters |

### Key change from original analysis

The original review treated cross-repo dependencies as "none exist, safe to delete." The revised view: **no consumers exist today, but the producer (Forge) and consumer infrastructure (nats-core topics, specialist-agent fleet) are now real and imminent**, not hypothetical.

---

## Revised Finding 3: Regression Analysis (Unchanged)

The regression analysis from the original review is unchanged. All references are in:
- Definition files: `kv-definitions.json`, `stream-definitions.json`
- Test files: `test_kv_definitions.py`, `test_kv_watch_integration.py`, `test_stream_definitions.py`, `test_readme_streams.py`
- Documentation: `README.md`, `docs/kv-usage.md`, `docs/design/specs/nats-infrastructure-system-spec.md`
- Provisioning: data-driven from `kv-definitions.json` (no script changes needed)

**No production consumer code. Regression risk remains Low.**

---

## Revised Finding 4: Future-Proofing (Revised Timeline)

### Original assessment
> "Revisit when dashboard/Jarvis needs live state" — trigger was described as hypothetical.

### Revised assessment

The trigger is now concrete and near-term:

| Trigger | Timeline | Explanation |
|---------|----------|-------------|
| Forge orchestrator publishes `BUILD_STARTED`/`BUILD_PROGRESS` | When Forge implementation begins | Natural point to also write KV state |
| specialist-agent needs pipeline awareness | After Forge integration | Agents need to know "is a build running?" before accepting new work |
| Jarvis relays build progress to adapters | After Forge + Jarvis integration | Jarvis watches KV for live state, pushes to Slack/Discord adapters |

### Reversibility confirmed

Adding `pipeline-state` back is still trivial:
1. Re-add entry to `kv-definitions.json` (~8 lines)
2. Re-add to `stream-definitions.json` (~4 lines)
3. Run `provision-kv.sh` (data-driven, no code changes)
4. Add a `NATSKVPipelineStateRegistry` to `nats-core` following the `NATSKVManifestRegistry` pattern
5. Forge writes KV state at each transition (dual-write alongside JetStream events)

Time estimate: **1-2 hours** for infrastructure; Forge producer code is part of the Forge build itself.

---

## Final Decision Matrix

| Criterion | Option A (Delete KV now) | Option B (Keep KV for live state) |
|-----------|-------------------------|-----------------------------------|
| Simplicity today | 10/10 | 7/10 (bucket exists but unused) |
| ADR alignment | Needs revision either way | Needs revision either way |
| Regression risk | Low | None (no change) |
| Cost of deletion | ~2 hours (9 files) | 0 |
| Cost of re-adding | ~1-2 hours when Forge needs it (days from now) | 0 |
| Net effort (delete + re-add) | ~3-4 hours of churn | 0 |
| Forge integration readiness | Must re-add bucket + tests + docs | Bucket ready, just needs consumer code in nats-core + Forge |
| **Overall Score** | **5/10** (churn penalty) | **9/10** |

---

## Final Recommendation

**Option B — keep the `pipeline-state` KV bucket as-is.**

The reasoning:

1. **Forge implementation is imminent** — the producer of pipeline state is days away, not months. Removing and re-adding is pure churn.
2. **The bucket is pre-provisioned readiness** — when Forge starts building, it writes KV state at each transition. Infrastructure is already there.
3. **nats-core has the KV pattern** — `NATSKVManifestRegistry` proves the design. A `PipelineStateRegistry` for `pipeline-state` follows the same approach.
4. **Events + KV state are complementary** — JetStream pipeline events (BUILD_PROGRESS etc.) carry event history. KV state answers "what is feature X doing *right now*?" Both are needed.
5. **specialist-agent is deploying** — real fleet agents will benefit from pipeline state visibility as soon as Forge starts orchestrating them.
6. **No regression risk** — we're keeping what exists. Zero files change.

### What needs to happen

| Action | Where | When |
|--------|-------|------|
| Record this decision | ADR in forge (amend ADR-SP-013 or new ADR-SP-018) | With Forge implementation |
| Update ADR-SP-013 | forge-pipeline-architecture.md | SQLite assumption needs revision — architecture is JetStream-native |
| Close ADR-SP-017's deferred question | forge-pipeline-architecture.md | Record: "pipeline-state KV kept for live cross-process state alongside JetStream events" |
| Add `PipelineStateRegistry` to nats-core | nats-core | When Forge producer code is built |
| Forge writes KV state at transitions | forge | Forge orchestrator implementation |
| Close TASK-PSKV-001 | nats-infrastructure | Now — decision is Option B |

### No file changes required in nats-infrastructure

The bucket definition, provisioning, tests, and documentation are all correct as-is. No changes needed.
