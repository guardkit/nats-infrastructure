# Memory Relay — Scope Document

Durable episode buffer + extraction trace capture for Graphiti (and any future
memory engine) across the Ship's Computer fleet.

**Date:** 2026-06-12
**Author:** Rich (drafted with Claude Desktop)
**Status:** Draft — input to `/feature-spec`
**Home repo:** `nats-infrastructure` (service + streams). Schemas/publisher in `nats-core`.
**Feature ID:** assigned by `/feature-plan`
**Explicitly NOT owned by:** guardkit. GuardKit is the *first publisher*, not the owner.

---

## 1. Problem Statement

Graphiti ingestion requires an LLM on the write path. Today that creates three
coupled failure modes, all observed in production:

1. **Memory loss when the extraction model is unloaded.** During FEAT-HMIG
   (AutoBuild → LangGraph/DeepAgents) work, `qwen-graphiti` is not resident and
   episodes are silently never captured. There is no durable record to replay.
2. **Cloud fallback cost.** The documented fallback when the GB10 is busy is
   Gemini 2.5 Pro — measured at ~£10/day during normal ingestion and ~£30 over
   one unattended weekend. This also violates the spirit of DECISION-DF-001.
3. **The 28 GB always-on pin.** `qwen-graphiti` (Qwen2.5-14B-FP8, 65K ctx) must
   stay preloaded *because writes can arrive at any moment*. Consolidation onto
   the workhorse failed (AUTOBUILD-ON-LLAMA-SWAP-findings §9.5–§9.7) and Gemma 4
   failed (§9.8), so the pin currently looks permanent.

**Root cause:** capture and extraction are synchronously coupled. Decouple them
with a durable buffer and all three problems become policy choices instead of
failures: capture is LLM-free and never lost; extraction is deferrable to when
(and only when) a local model is resident; the extraction model becomes
schedulable rather than always-on.

A fourth requirement rides along: **capture real extraction request/response
pairs at the serving layer** so that a future fine-tuned/distilled extraction
model (dataset-factory exemplar) has a training corpus that accumulates from
today with zero authoring effort.

---

## 2. Decision Log

These become ADRs seeded to Graphiti (`group_id` with underscores). The
implementing model must NOT revisit them.

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|--------|
| D1 | Durable episode buffer on NATS JetStream (`MEMORY` stream) | JetStream already deployed, file-backed, replayable; episodes are knowledge, not transient coordination | graphiti MCP server's in-process async queue (not durable — dies with the process); direct ingestion with retry loops (loses data when model absent for hours/days) | Proposed |
| D2 | Capture is **always-buffer, single write path** — producers never call Graphiti directly | One code path; capture is LLM-free, instant, and identical whether the model is resident or not. Near-real-time behaviour is preserved because the drain worker consumes immediately when the model is resident | Dual-mode (direct when model up, buffer when down): two code paths, race conditions, harder to test | Proposed |
| D3 | Schemas + publisher helper live in **nats-core** | Fleet-wide requirement: guardkit, jarvis, forge, specialist-agent, lpa-platform-poc, the Graphiti MCP path, and future agents all publish via the same package (`pip install git+ssh` per ADR-SP-009) | Publisher in guardkit (couples fleet memory to one tool — explicitly ruled out); per-repo copies (drift) | Proposed |
| D4 | Drain worker (`memory-relay`) is a **standalone service deployed from nats-infrastructure** (compose service alongside the NATS server) | It is infrastructure, not an agent: owns the streams it consumes, co-deploys with them. Exemplar-before-template: promote to its own repo only if it grows beyond one deployable | guardkit CLI subcommand (ties drain to guardkit installs); new repo now (premature; one more thing to operate) | Proposed |
| D5 | Drain is **gated on extraction-model residency**, with three triggers: opportunistic (residency probe), scheduled window, manual command | The §9.5 failure was burst concurrency + synchronous timeout pressure. A gated drain with concurrency matched to actual serving capacity removes both. Probe must be **non-loading** (a `/v1` completion probe would trigger a swap) — use llama-swap's resident-model admin endpoint (`/running` in current builds; verify exact path at implementation) | Always-drain with retries (recreates the synthetic-429 failure); model-load-on-publish (defeats the point) | Proposed |
| D6 | Episodes are **retained after successful ingestion** (long-retention stream; ack ≠ delete is achieved by `limits` retention, not `workqueue`) | The stream becomes the canonical raw event record. Replay = re-ingest: this is the migration insurance if the engine ever changes (Hindsight evaluation), and the recovery path after any graph corruption/clear | Work-queue retention (message destroyed on ack — loses the canonical record); interest retention (same problem) | Proposed |
| D7 | Episode schema is **framework-neutral** — no Graphiti-specific fields in `MemoryEpisodeV1`; engine-specific mapping lives in the drain worker | The buffer must outlive any one engine. A Hindsight (or custom) drain target is a new consumer, not a schema migration | Embedding Graphiti parser/episode-type semantics in the payload | Proposed |
| D8 | Extraction traces captured at the **serving layer** via a thin logging reverse proxy in front of llama-swap for extraction-model traffic, published as `ExtractionTraceV1` | Catches every consumer (guardkit CLI, MCP server, future agents) regardless of client code; the working Qwen2.5-14B pipeline is the teacher — "teacher funds its own replacement", locally | Client-side logging in guardkit (misses MCP + other consumers); LangSmith-only (cloud, partial coverage, not dataset-shaped) | Proposed |
| D9 | Idempotency via `Nats-Msg-Id: {episode_id}` (JetStream server-side dedupe window) + drain-worker ledger of ingested episode IDs | At-least-once delivery is guaranteed; double-ingestion into the graph must be prevented at two layers | Exactly-once assumptions; dedupe only in the graph (Graphiti dedup is LLM-mediated and was a failure surface in §9.8) | Proposed |
| D10 | Once the drain worker is validated, **`qwen-graphiti` moves out of the always-on preload group** into the swap matrix | This is the ~28 GB reclaim during interactive/AutoBuild hours, achieved architecturally with zero model-quality gamble. The §9.4 steady-state drops from ~83 GB toward ~55 GB during drain-idle periods | Model substitution (workhorse §9.5/§9.6, Gemma 4 §9.8 — both failed); accepting the pin | Proposed |
| D11 | `group_id` values use **underscores only** | FalkorDB/RediSearch syntax errors on hyphens (established convention, all repos migrated) | — | Accepted (existing) |

**Warnings & constraints** (seed as Graphiti warning nodes):

- Drain concurrency MUST match the serving layer's real capacity:
  `chunk_extraction_concurrency` ≤ llama.cpp `-np` slots / `concurrencyLimit`
  (currently 4/6 on `qwen-graphiti`), or vLLM `--max-num-seqs` if the backend
  changes. Exceeding it recreates the §9.5 synthetic-429 cascade.
- Graphiti episode ingestion can legitimately run minutes (multi-call fan-out,
  ~7.8K-token prompt scaffolding per call). Consumer `ack_wait` must exceed the
  worst observed episode time (set 900s; the 600s pipeline timeout fires first).
- NATS default max payload is ~1 MB. Episode bodies are raw documents — chunks
  near the limit must be split by the publisher (publisher helper enforces a
  900 KB ceiling and rejects/splits above it). Do NOT raise server max_payload
  casually; it affects every stream.
- The llama-swap keepalive timer revives preloaded models every ~5 min. The
  drain worker's scheduled-window trigger must coordinate with it the same way
  coder-next builds do (§9.2) if it ever intentionally loads/evicts models.
- Subjects must respect NATS account permissions: client-account producers
  (e.g. FINPROXY) cannot publish to `memory.>` — see Open Decision O1.
- `.env`/secrets: the trace proxy logs full request/response bodies. Bodies are
  development knowledge on owned hardware — acceptable — but the proxy MUST
  redact `Authorization` headers before publishing.

---

## 3. Architecture

### 3.1 System context

```
 Producers (any fleet member)                nats-core publisher helper
 ┌──────────┐ ┌────────┐ ┌───────┐ ┌──────────────┐
 │ guardkit │ │ jarvis │ │ forge │ │ lpa-poc, ... │      LLM-free, instant
 └────┬─────┘ └───┬────┘ └───┬───┘ └──────┬───────┘
      └───────────┴─────┬────┴────────────┘
                        ▼  publish MemoryEpisodeV1
              ╔═══════════════════════╗
              ║  JetStream: MEMORY    ║   durable, long retention,
              ║  memory.episode.>     ║   canonical raw event record
              ╚═══════════╤═══════════╝
                          │ durable pull consumer (gated)
                          ▼
                ┌───────────────────┐   residency probe ──► llama-swap :9000
                │  memory-relay     │   (non-loading)        (qwen-graphiti)
                │  drain worker     │──────────────────────► /v1/chat/completions
                │  (this repo)      │                        via trace proxy :9001
                └─────────┬─────────┘
                          │ graphiti-core add_episode (per-project config)
                          ▼
                   FalkorDB (Synology NAS, Tailscale)

 Trace path (D8):
 graphiti-core ──► trace proxy :9001 ──► llama-swap :9000
                        │ publish ExtractionTraceV1
                        ▼
              ╔═══════════════════════╗
              ║ JetStream:            ║   training corpus for future
              ║ MEMORY_TRACES         ║   distilled extraction model
              ╚═══════════════════════╝
```

### 3.2 Components

| Component | Repo / Path | Purpose | New/Modified |
|-----------|-------------|---------|--------------|
| `MemoryEpisodeV1`, `ExtractionTraceV1`, `DrainReportV1` Pydantic schemas | `nats-core` → `nats_core/schemas/memory.py` | Versioned payloads | New (cross-repo) |
| Publisher helper (`publish_episode()`, size guard, Msg-Id) | `nats-core` → `nats_core/memory/publisher.py` | One-call capture for any producer | New (cross-repo) |
| Stream definitions: `MEMORY`, `MEMORY_TRACES` | `nats-infrastructure` → `streams/stream-definitions.json` | Declarative provisioning | Modified |
| Consumer definitions (durable pull, backoff, DLQ policy) | `nats-infrastructure` → `streams/` (extend provisioning) | Drain consumers | Modified |
| `memory-relay` drain worker | `nats-infrastructure` → `services/memory_relay/` | Gated drain → Graphiti ingestion | New |
| Worker config (project registry) | `nats-infrastructure` → `config/memory-relay.yaml` | project_id → graphiti settings map | New |
| Trace proxy | `nats-infrastructure` → `services/trace_proxy/` | :9001 → :9000 reverse proxy, publishes traces | New |
| Compose services `memory-relay`, `trace-proxy` | `nats-infrastructure` → `docker-compose.yml` | Deployment | Modified |
| GuardKit publisher integration (`graphiti add-context` / `capture-outcome` → publish) | `guardkit` | First producer (exemplar) | New (cross-repo, **created only on explicit instruction**) |
| llama-swap preload change (qwen-graphiti → swap group) | GB10 `/opt/llama-swap/config/config.yaml` + findings doc §9.x entry | The 28 GB reclaim (D10) | Modified (ops, gated on validation) |

Per repo-scope discipline: tasks in `nats-core` and `guardkit` are listed for
coordination; they are separate `/feature-plan` items in those repos.

### 3.3 Data flow (primary case)

1. Producer calls `publish_episode(project_id, group_id, episode_type, name, body, source_ref)`.
2. Helper validates schema, enforces ≤900 KB body, sets `Nats-Msg-Id = episode_id`, publishes to `memory.episode.{project_id}.{episode_type}`.
3. JetStream `MEMORY` stream stores it (server-side dedupe window absorbs producer retries).
4. `memory-relay` probe finds `qwen-graphiti` resident (or a scheduled window opens, or `drain --now`).
5. Worker pulls a batch (size = configured drain concurrency), maps each episode to graphiti-core `add_episode` using the project registry (engine-specific mapping lives HERE, per D7).
6. Success → ack + record episode_id in the ingestion ledger + emit `DrainReportV1` on `memory.drain.{project_id}`.
7. Failure → nak with backoff; after `max_deliver` exhaustion, republish payload to `memory.dlq.{project_id}` and ack (poison-message quarantine, alert via `notifications.>`).

### 3.4 Message schemas

`MemoryEpisodeV1` — framework-neutral (D7):

```json
{
  "schema": "memory.episode.v1",
  "episode_id": "uuid-v4",
  "project_id": "guardkit",
  "group_id": "architecture_decisions",
  "episode_type": "adr | feature_outcome | review_report | document | conversation | structured_json",
  "name": "ADR-DF-014 ...",
  "body": "raw pre-extraction content (text or JSON string)",
  "content_format": "markdown | text | json",
  "source": "guardkit-cli | autobuild | mcp | jarvis | forge | manual",
  "source_ref": "repo-relative path / TASK-XXX / build_id",
  "occurred_at": "ISO-8601",
  "published_at": "ISO-8601",
  "ingest_hints": { "parser": "full_doc | message | json", "priority": "normal | low" }
}
```

`ExtractionTraceV1`:

```json
{
  "schema": "memory.trace.v1",
  "trace_id": "uuid-v4",
  "model": "qwen-graphiti",
  "endpoint": "/v1/chat/completions",
  "request": { "...full body, auth headers redacted..." },
  "response": { "...full body..." },
  "status": 200,
  "latency_ms": 1234,
  "episode_id": "uuid | null  (via X-Memory-Episode-Id header if propagated)",
  "captured_at": "ISO-8601"
}
```

`DrainReportV1`: `{schema, project_id, drained, failed, dlq, window, started_at, finished_at, model, wall_seconds}`.

### 3.5 Stream definitions (proposed entries for `stream-definitions.json`)

```json
{
  "name": "MEMORY",
  "subjects": ["memory.episode.>", "memory.drain.>", "memory.dlq.>"],
  "retention": "limits",
  "max_age": "365d",
  "max_msgs": 100000,
  "storage": "file",
  "replicas": 1,
  "scope": "core",
  "description": "Durable memory episodes (canonical raw record), drain reports, DLQ"
},
{
  "name": "MEMORY_TRACES",
  "subjects": ["memory.trace.>"],
  "retention": "limits",
  "max_age": "180d",
  "max_msgs": 500000,
  "storage": "file",
  "replicas": 1,
  "scope": "core",
  "description": "Extraction LLM request/response pairs — training corpus for distilled extraction model"
}
```

Consumer (provisioned alongside): durable pull `memory-drain`, filter
`memory.episode.>`, `ack_wait: 900s`, `max_deliver: 5`,
`backoff: [30s, 2m, 10m, 30m]`, `max_ack_pending:` = drain concurrency.

### 3.6 Drain worker behaviour

- **Triggers:** (a) opportunistic — probe llama-swap every `probe_interval`
  (default 120s); drain while model resident AND queue non-empty; (b)
  scheduled — cron windows (e.g. `02:00–06:00`) during which the worker may
  itself request the model load via a single completion probe, drain to empty,
  then leave eviction to the matrix solver; (c) manual —
  `memory-relay drain --project <id> [--now]`.
- **Concurrency:** `episode_parallelism` (default 1 — episodes sequential) ×
  graphiti-core `SEMAPHORE_LIMIT` set from config (default 4, matching
  `qwen-graphiti` `-np 4`). Deliberately conservative: throughput is a
  non-goal; durability and zero synthetic-429s are the goals.
- **Backpressure honesty:** if an episode exceeds `episode_timeout` (default
  900s), nak and stand down for `cooloff` (default 10 min) — the box is busy.
- **Idempotency ledger:** SQLite (or KV bucket `memory-ingested`) of
  episode_ids successfully ingested per project; checked before `add_episode`.
- **Observability:** `DrainReportV1` per run; counters into the existing
  `system.>` health pattern; LangSmith tagging optional (`{client: internal,
  feature_id: FEAT-MEMR}`) for cost attribution parity.

### 3.7 Trace proxy

Thin ASGI reverse proxy (`:9001 → :9000`), pass-through for all routes,
fire-and-forget publish of `ExtractionTraceV1` for configured model aliases
(initially `qwen-graphiti` only). Repoint `llm_base_url` in each project's
`graphiti.yaml` to `:9001`. Failure mode: if NATS publish fails, the proxy
still forwards (capture is best-effort; serving is not). Downstream
ShareGPT-JSONL conversion for the dataset factory is a separate consumer job —
**out of scope here**; this scope only guarantees the corpus accumulates.

---

## 4. Open Decisions (resolve in `/feature-spec`)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| O1 | Client-account projects (FINPROXY) — subject scheme | (a) `finproxy.memory.>` added to FINPROXY stream + second consumer; (b) APPMILLA-side mirror; (c) defer | (c) defer — lpa-platform-poc memory currently flows under Rich's account; revisit when a client needs isolated memory |
| O2 | Graphiti MCP server writes (Claude Desktop sessions) | (a) leave direct (model must be resident for interactive use anyway); (b) route via buffer too | (a) for Phase 1–5; interactive MCP use implies the model is wanted *now*. Revisit if MCP write loss is observed |
| O3 | Ledger store | SQLite in worker volume vs JetStream KV bucket | KV bucket `memory-ingested` — consistent with existing KV usage, survives container rebuilds |
| O4 | Drain worker also handles re-seed/replay (`memory-relay replay --project X --since ...`) | in MVP vs later | Later (Phase 6+) — but D6/D7 guarantee it's possible |
| O5 | Trace capture for non-extraction models (workhorse agent traffic) | now vs later | Later — different corpus, different consent-to-volume trade |

---

## 5. Implementation Phases

Each phase is decomposable by `/feature-plan`; cross-repo phases are created in
their home repos only on explicit instruction.

| Phase | Repo | Deliverable | Acceptance |
|-------|------|-------------|------------|
| P1 | nats-core | Schemas + publisher helper + unit tests | `publish_episode()` round-trips against local NATS; >900 KB body rejected with actionable error; Msg-Id set |
| P2 | nats-infrastructure | Stream/consumer definitions + provisioning + tests | `provision-streams.sh --dry-run` then live run shows `[CREATE]` for MEMORY, MEMORY_TRACES; `tests/test_stream_definitions.py` extended and green |
| P3 | nats-infrastructure | `memory-relay` MVP (opportunistic + manual triggers, ledger, DLQ) + compose service | Publish 3 episodes with model unloaded → queue holds; load `qwen-graphiti` → drain completes, FalkorDB shows episodes, ledger prevents re-ingest on redelivery |
| P4 | guardkit | `graphiti add-context` / `capture-outcome` publish via nats-core helper (keep `--direct` escape hatch for one release) | Existing guardkit Graphiti tests pass through the buffered path; episode appears in graph ≤ probe_interval when model resident |
| P5 | nats-infrastructure | Trace proxy + repoint guardkit `graphiti.yaml` to :9001 | One real `add-context` run yields N traces in MEMORY_TRACES with redacted auth; latency overhead < 50 ms p95 |
| P6 | ops (GB10) | `qwen-graphiti` out of always-on preload (D10) + findings-doc §9.x entry | One week: zero lost episodes (stream audit vs graph), steady-state memory during interactive hours reduced by ~28 GB, scheduled window drains to empty |

## 6. Validation Gates

| Gate | Test | PASS criterion |
|------|------|----------------|
| G1 | Kill-the-model durability | Publish during model-absent period; 100% of episodes ingested after next drain; 0 silent losses |
| G2 | §9.5 regression guard | Drain a 10-episode backlog incl. one ~9K-token chunk doc; 0 synthetic-429/SDK-retry storms; 0 `exceed_context_size` |
| G3 | Idempotency | Force redelivery (restart worker mid-batch); graph episode count unchanged |
| G4 | Poison message | Malformed body → DLQ after max_deliver, alert emitted, drain continues |
| G5 | Trace corpus | 1 week of normal use accumulates ≥ hundreds of trace pairs, parseable to ShareGPT JSONL in a notebook spike |
| G6 | Cloud fallback retired | Gemini fallback block removed from `graphiti.yaml`s; £0 cloud spend on memory path |

## 7. Revisit Conditions

- **Second GB10 Spark lands (256 GB pool):** D10's urgency drops; durability
  (D1–D9) remains fully justified. Do not unwind.
- **Upstream PR gate (guardkit/graphiti fixes #5, #8–#12, 8-week window):**
  merged → unpin fork; stalled → promote Hindsight evaluation to migration
  candidate. Either way the buffer and trace corpus carry over (D6/D7).
- **vLLM-workhorse unification experiment (separate TASK-REV):** if G1–G4 of
  that experiment pass, the drain worker simply gets a different residency
  target and higher concurrency; no schema or stream changes.
- **Qwen2.5-7B drop-in experiment (separate TASK-REV):** if extraction quality
  holds, `qwen-graphiti` shrinks ~28 GB → ~9 GB; drain worker unchanged.
- **Distilled extraction model ready (dataset factory):** MEMORY_TRACES is its
  corpus; drain worker repoints `llm_model`; everything else unchanged.

## 8. Related Documents

- `guardkit/docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md` §9.1–§9.8
- `guardkit/docs/reference/graphiti-llm-selection.md` (TASK-REV-DGX1)
- `guardkit/.guardkit/graphiti.yaml` (current single-source config to be split: capture vs drain concerns)
- `nats-infrastructure/docs/design/decisions/ADR-001-standalone-infra-repo.md`
- `dev-pipeline-architecture.md` §10 (Graphiti integration points — superseded in part by this scope: ingestion moves from "within the AutoBuild process" to "via the MEMORY stream")
