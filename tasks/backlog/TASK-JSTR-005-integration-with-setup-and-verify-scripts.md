---
id: TASK-JSTR-005
title: "Integration with setup-gb10.sh and verify-nats.sh"
task_type: feature
parent_review: TASK-REV-E14C
feature_id: FEAT-JSTR
wave: 3
implementation_mode: direct
complexity: 2
dependencies: [TASK-JSTR-002]
status: pending
priority: normal
tags: [integration, setup, verification]
estimated_minutes: 20
---

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
