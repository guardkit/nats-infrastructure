---
id: TASK-NATS-002
title: Create account configuration files with envsubst templates
status: completed
task_type: scaffolding
parent_review: TASK-REV-69BD
feature_id: FEAT-NATS-CFG
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-NATS-001
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-D2AD
  base_branch: main
  started_at: '2026-04-08T09:44:19.390745'
  last_updated: '2026-04-08T09:52:02.052584'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T09:44:19.390745'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

> **[WS3-S8 tracker sweep 2026-07-11]** Status reconciled to `completed`. Was `in_review` under `backlog/` (inferred_completion_conflict). Feature **FEAT-D2AD** is `status: completed`; deliverables shipped on `main` (pointer commit `e0bac6a`). No code changed by this sweep.

# Create Account Configuration Files with envsubst Templates

## Description

Create NATS account configuration files under `config/accounts/` implementing the multi-tenancy model from ADR-002. Use `envsubst`-compatible templates (e.g., `${RICH_NATS_PASSWORD}`) so credentials are substituted from `.env` at container startup time. NATS config does not natively interpolate environment variables, so the Docker entrypoint or a startup wrapper must run `envsubst` before launching `nats-server`.

## Requirements

Based on system spec Feature 2 and ADR-002:

### Accounts

| Account | Users | Permissions | JetStream |
|---------|-------|-------------|-----------|
| APPMILLA | rich, james | publish: `>`, subscribe: `>` | enabled |
| FINPROXY | mark | publish: `finproxy.>`, subscribe: `finproxy.>` | enabled |
| SYS | admin | system account | N/A |

### Template Variables

- `${RICH_NATS_PASSWORD}` — Rich's APPMILLA password
- `${JAMES_NATS_PASSWORD}` — James's APPMILLA password
- `${MARK_NATS_PASSWORD}` — Mark's FINPROXY password
- `${ADMIN_NATS_PASSWORD}` — SYS admin password

### envsubst Integration

Create a wrapper script or Docker entrypoint that:
1. Reads template configs from `config/accounts/*.conf.template`
2. Runs `envsubst` to produce runtime configs at `/etc/nats/accounts/*.conf`
3. Launches `nats-server` with the processed config

## Acceptance Criteria

- [ ] `config/accounts/accounts.conf.template` exists with all three accounts (APPMILLA, FINPROXY, SYS)
- [ ] Template uses `${VAR}` syntax for all password fields
- [ ] APPMILLA account: rich + james users with full pub/sub access, JetStream enabled
- [ ] FINPROXY account: mark user scoped to `finproxy.>` only, JetStream enabled
- [ ] SYS account: admin user, designated as system_account
- [ ] `scripts/docker-entrypoint.sh` runs `envsubst` then `exec nats-server`
- [ ] No plaintext passwords committed to repository

## Implementation Notes

- Single accounts file is simpler than per-account files for a 3-account setup
- The `system_account: SYS` directive must be at the top level of nats-server.conf (outside the accounts block), or handled via include ordering
- `envsubst` is available in the `nats:latest` Docker image (based on Alpine, may need to add `gettext` package)
- Alternative: use a multi-stage Docker build or init container to preprocess templates
- Test with placeholder passwords first; real passwords go in `.env` (gitignored)
