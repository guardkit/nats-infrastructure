# Memory Write Path v2 — post-Graphiti reconciliation

**Date:** 2026-06-24
**Status:** Reconciliation spec — input to `/feature-spec` / `/feature-plan` (per-repo)
**Supersedes:** [`memory-relay-scope.md`](memory-relay-scope.md) (2026-06-12, Graphiti-era)
**Repos:** publisher → `nats-core`; stream + identity → `nats-infrastructure`; consumer → `fleet-memory`
**Driving decision:** **Graphiti is being decommissioned ASAP; fleet-memory (deterministic Postgres + pgvector, LLM-free writes) is the memory substrate going forward.** This collapses the Graphiti-era design — roughly half of it was machinery to *feed and retire the Graphiti extraction model* and no longer applies.

---

## 1. Why this supersedes the 2026-06-12 scope

The original scope solved one problem: **an LLM (`qwen-graphiti`) sat on the write path**, so capture had to be decoupled from slow/expensive/always-on extraction. Every Graphiti-specific mechanism (residency-gated drain, 900 s ack_wait, the trace proxy + `MEMORY_TRACES` corpus to train a distilled extractor, the 28 GB preload reclaim) exists *only* because of that LLM.

fleet-memory removes the LLM from the write path entirely (deterministic UUIDv5 / content-hash upsert, embed-on-write, zero-LLM). So those mechanisms are not "deferred" — they are **obsolete**. What remains valuable from the scope doc is the **transport/buffer contract**, which is engine-neutral.

Building blindly to the old scope (mechanical "align to the spec") would import dead assumptions — that is the not-fit-for-purpose risk this doc exists to remove.

## 2. Decision log v2 (Δ from the original)

| Orig | Decision | v2 verdict |
|---|---|---|
| D1 | Durable `MEMORY` JetStream stream as canonical raw record | **KEEP** |
| D2 | Capture is always-buffer, single LLM-free write path; producers never call the engine directly | **KEEP** |
| D3 | Schemas + `publish_episode()` helper live in **nats-core** | **KEEP** — still unbuilt; this is the real unblock for the harvest |
| D4 | Consumer is a Graphiti-drain worker in nats-infrastructure | **REPLACE** → the consumer is the **fleet-memory relay** (`src/fleet_memory/relay/`, already built), writing to Postgres+pgvector |
| D5 | Drain gated on extraction-model residency (probe/window/manual) | **DROP** — no model on the write path; the relay consumes continuously |
| D6 | Episodes retained after ingest (`limits`, long retention) — replay insurance | **KEEP** — stream stays the canonical replayable record; Postgres is the queryable store |
| D7 | Framework-neutral `MemoryEpisodeV1` | **KEEP** — reconcile the two existing schemas into one canonical (see §5) |
| D8 | Trace proxy → `ExtractionTraceV1` → `MEMORY_TRACES` | **DROP** — training corpus for the Graphiti-extractor replacement; no extractor, no traces |
| D9 | Idempotency: `Nats-Msg-Id` dedupe + ingest ledger | **KEEP & SIMPLIFY** — `Nats-Msg-Id={episode_id}` (stream-level) + the relay's existing deterministic UUIDv5/content-hash upsert *is* the second layer; no separate ledger needed |
| D10 | Move `qwen-graphiti` out of always-on preload (28 GB reclaim) | **MOVE** — this is just Graphiti decommissioning (fleet-memory FEAT-MEM-09), not part of the write path |
| D11 | `group_id` underscores-only (FalkorDB constraint) | **N/A** — FalkorDB-specific; fleet-memory uses namespace tuples (see §5 on `group_id`) |

**New v2 decisions:**

- **V1** — The relay is a **durable PULL consumer** with filter `memory.episode.>`, `ack_policy=explicit`, `max_deliver=5`, **`ack_wait` short (recommend 60 s)** — a deterministic embed + Postgres commit is seconds, not the 900 s Graphiti extraction window. Ack-after-commit.
- **V2** — Poison (`PoisonEpisodeError`) → `term` + explicit publish to `memory.dlq.{project_id}`, retained in the `MEMORY` stream for inspection; transient → `nak` (redeliver ≤ max_deliver). No auto-DLQ from JetStream.
- **V3** — A dedicated **`fleet-memory` NATS user** (APPMILLA account) is required: subscribe/consume `memory.episode.>`, publish `memory.dlq.>`, + JetStream API perms. None exists today (the dedicated user created on the GB10 is `forge`, unrelated).

## 3. Architecture (post-Graphiti)

```
 Producers (guardkit harvest first, then jarvis/forge/…)
        │  publish_episode(project_id, episode_type, body, …)   ← nats-core helper (LLM-free, instant)
        ▼  subject: memory.episode.{project_id}.{episode_type}   Nats-Msg-Id = episode_id
 ╔════════════════════════════════════════╗
 ║ JetStream: MEMORY                       ║  durable, limits/long retention,
 ║ subjects: memory.episode.>, memory.dlq.>║  canonical replayable record
 ╚════════════════════╤═══════════════════╝
                      │ durable pull consumer (filter memory.episode.>, explicit ack)
                      ▼
            ┌──────────────────────┐
            │ fleet-memory relay   │  json → payload registry → deterministic writer
            │ (src/fleet_memory/   │  md/text → heading-aware chunk → embed-on-write
            │  relay/)             │  poison → memory.dlq.{project_id}
            └──────────┬───────────┘
                       ▼
            Postgres 16 + pgvector (NAS whitestocks:5433)   ← store of record
```

Dropped vs the original diagram: the residency probe, the Graphiti `add_episode` path, FalkorDB, the trace proxy, and `MEMORY_TRACES`.

## 4. Stream + consumer contract (replaces scope §3.5)

`stream-definitions.json` — single stream:

```json
{
  "name": "MEMORY",
  "subjects": ["memory.episode.>", "memory.dlq.>"],
  "retention": "limits",
  "max_age": "365d",
  "max_msgs": 100000,
  "storage": "file",
  "replicas": 1,
  "scope": "core",
  "description": "Durable memory episodes (canonical raw record) + DLQ; consumed by the fleet-memory relay → Postgres"
}
```

(No `MEMORY_TRACES`. No `memory.drain.>` — there is no gated drain. A relay-outcome/report subject can be added later if observability needs it.)

Durable pull consumer (provisioned alongside, or declared by the relay subscriber with `declare=False` stream bind): `durable=fleet-memory-relay`, `filter_subject=memory.episode.>`, `ack_policy=explicit`, `max_deliver=5`, `ack_wait=60s`, modest `backoff`.

## 5. Schema reconciliation (the one real design task)

Two `MemoryEpisodeV1` definitions exist and disagree. nats-core owns the canonical one (D3); fleet-memory imports/mirrors it.

| Field | scope-doc (2026-06-12) | fleet-memory relay (built) | v2 canonical (recommend) |
|---|---|---|---|
| project key | `project_id` | `project` | **`project_id`** (matches the subject partition); rename in the relay |
| episode category | `episode_type` (adr/feature_outcome/…/structured_json) | `payload_type` (typed-payload-registry key) | keep **both**: `episode_type` = coarse source category; `payload_type` = registry key for the json path. Clarify in /feature-spec |
| `content_format` | json/markdown/text | raw str (json/markdown/text) | **KEEP** (raw str, `extra=ignore` survives unknowns) |
| `body`, `source_ref`, `episode_id` | present | present | **KEEP** |
| `name`, `source`, `occurred_at`, `published_at`, `ingest_hints` | present | absent | add as **optional** (relay already `extra=ignore`s them; promote to typed fields) |
| `group_id` | present (FalkorDB grouping) | absent | **DROP** from the canonical write contract — fleet-memory partitions by namespace `(fleet_memory, project_id, kind)`, not FalkorDB group_id |

Open for `/feature-spec`: (a) `project` → `project_id` rename across relay + writer + tests; (b) `episode_type` ↔ `payload_type` relationship and whether `episode_type` drives routing; (c) which of name/source/timestamps the writer actually persists.

## 6. Build sequence

| Phase | Repo | Deliverable | Unblocks |
|---|---|---|---|
| **P1** | nats-core | canonical `MemoryEpisodeV1` + `publish_episode()` (Nats-Msg-Id, ≤900 KB guard) + tests | the producer the relay lacks |
| **P2** | nats-infrastructure | `MEMORY` stream (`memory.episode.>`/`memory.dlq.>`) in defs + provisioning + `fleet-memory` NATS user (V3) | live transport + identity |
| **P3** | fleet-memory | relay subject → `memory.episode.>`, schema → nats-core canonical, `ack_wait` 60 s; deploy + RLY-007 live verify | the write path runs end-to-end |
| **P4** | guardkit | harvest publishes via the nats-core helper | **"run the harvest on the GB10"** |

Dropped from the old phase plan: trace proxy / `MEMORY_TRACES` (P5) and the qwen reclaim (P6 → folded into Graphiti decommission FEAT-MEM-09).

## 7. What the existing relay build keeps vs corrects

- **Keeps:** durable pull consumer wiring, explicit ack / nak / term, `max_deliver` from settings, registry dispatch, heading-aware chunker, chunk writer, deterministic writer integration, the 85-test suite (logic is sound).
- **Corrects:** subject `memory.episode` → `memory.episode.>`; DLQ `memory.dlq` → `memory.dlq.{project_id}`; schema field `project` → `project_id` (+ optional fields); `ack_wait` to 60 s. (My uncommitted WIP in fleet-memory + nats-infrastructure is the durable-consumer wiring and a *flat* stream — the wiring survives, the flat subjects get replaced by the above.)

## 8. Validation gates (adapted)

| Gate | Test | PASS |
|---|---|---|
| G1 | Durability — publish with relay down; bring it up | 100% of episodes written to Postgres, 0 loss |
| G2 | Idempotency — force redelivery (restart mid-batch) | Postgres row count unchanged (UUIDv5/content-hash upsert + Msg-Id dedupe) |
| G3 | Poison → DLQ | malformed body → `memory.dlq.{project}` after max_deliver, relay continues |
| G4 | Empty/partial | empty-prose → ack + 0 chunks; partial-chunk redelivery → clean idempotent overwrite |
| G5 | Parity (migration) | probe-set retrieval parity vs Graphiti baseline (FEAT-MEM-05 harness) before cutover |

(Dropped: §9.5 synthetic-429 regression, trace-corpus, cloud-fallback — all Graphiti-extraction gates.)

## 9. Related

- Supersedes [`memory-relay-scope.md`](memory-relay-scope.md); that doc remains for historical rationale (the LLM-on-write-path problem).
- fleet-memory consumer contract: `fleet-memory/docs/decisions/MEM-04-relay-jetstream-contract.md` (to be updated to point here).
- Migration framing: `forge/docs/reviews/forge-fleet-state-review-2026-06-24.md` (fleet-memory replaces Graphiti).
