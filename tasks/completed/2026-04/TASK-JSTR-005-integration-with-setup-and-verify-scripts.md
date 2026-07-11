---
id: TASK-JSTR-005
title: Integration with setup-gb10.sh and verify-nats.sh
task_type: feature
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 2
dependencies:
- TASK-JSTR-002
status: completed
priority: normal
tags:
- integration
- setup
- verification
estimated_minutes: 20
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-7044
  base_branch: main
  started_at: '2026-04-13T22:16:16.667777'
  last_updated: '2026-04-13T22:29:38.618347'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-13T22:16:16.667777'
    player_summary: "Implemented two changes per the task spec: (1) Created scripts/setup.sh\
      \ \u2014 a 5-step setup script that orchestrates the full NATS infrastructure\
      \ deployment sequence. Step 4 calls provision-streams.sh after Docker Compose\
      \ up (step 3) and before verify-nats.sh (step 5). The provisioning step is gracefully\
      \ gated on nats CLI and jq availability. (2) Extended scripts/verify-nats.sh\
      \ with a new Check 5 section that iterates over all 7 expected streams (PIPELINE,\
      \ AGENTS, JARVIS, NOTIFICATIONS, SYSTEM, FLE"
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-7044** is `status: completed`; deliverables shipped on `main` (pointer commit `8f0dce0`). No code changed by this sweep.

# Task: Integration with setup and verify scripts

## Description

Ensure `provision-streams.sh` is called from `setup-gb10.sh` (step 4 in the spec) and extend `verify-nats.sh` to check that expected streams exist after provisioning.

## Changes

### setup-gb10.sh

Add stream provisioning as step 4 (after Docker Compose up, before verification):

```bash
# 4. Provision JetStream streams
echo "Provisioning JetStream streams..."
./streams/provision-streams.sh
```

Note: `setup-gb10.sh` may not exist yet (depends on TASK-REV-1A6B Docker Compose feature). If it doesn't exist, create a stub that will be extended later.

### verify-nats.sh

Add a Check 5 section that verifies expected streams exist:

```bash
# Check 5: JetStream streams provisioned
if command -v nats &> /dev/null; then
    echo "Check 5: JetStream streams..."
    EXPECTED_STREAMS="PIPELINE AGENTS JARVIS FLEET NOTIFICATIONS SYSTEM FINPROXY"
    for stream in $EXPECTED_STREAMS; do
        if nats stream info "$stream" --json &>/dev/null; then
            echo "  [OK] $stream"
        else
            echo "  [MISSING] $stream"
        fi
    done
fi
```

## Acceptance Criteria

- [ ] `provision-streams.sh` called from setup script at correct point in sequence
- [ ] `verify-nats.sh` lists all expected streams with `[OK]`/`[MISSING]` status
- [ ] Stream verification is gated on `nats` CLI availability (graceful skip)
- [ ] All modified files pass project-configured lint/format checks with zero errors
