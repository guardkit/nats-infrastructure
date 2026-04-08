---
id: TASK-NATS-003
title: Create .env.example with all configuration variables
status: in_review
task_type: scaffolding
parent_review: TASK-REV-69BD
feature_id: FEAT-NATS-CFG
wave: 3
implementation_mode: direct
complexity: 2
dependencies:
- TASK-NATS-002
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/worktrees/FEAT-D2AD
  base_branch: main
  started_at: '2026-04-08T09:52:02.068109'
  last_updated: '2026-04-08T09:56:27.903000'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T09:52:02.068109'
    player_summary: 'Created .env.example at the repository root documenting all 4
      required NATS password environment variables (RICH_NATS_PASSWORD, JAMES_NATS_PASSWORD,
      MARK_NATS_PASSWORD, ADMIN_NATS_PASSWORD) with ''changeme'' placeholder values.
      Each variable has detailed comments explaining its purpose, which NATS account
      it belongs to, and that it has no default value. The file includes a header
      with setup instructions (cp .env.example .env). Updated README.md Quick Start
      section to include the .env.example copy '
    player_success: true
    coach_success: true
---

# Create .env.example with All Configuration Variables

## Description

Create a `.env.example` file documenting all environment variables required by the NATS infrastructure deployment. This serves as the canonical reference for what needs to be configured before running `docker compose up`.

## Requirements

### Required Variables

```bash
# NATS Account Passwords
RICH_NATS_PASSWORD=changeme
JAMES_NATS_PASSWORD=changeme
MARK_NATS_PASSWORD=changeme
ADMIN_NATS_PASSWORD=changeme
```

### Documentation

Each variable should have a comment explaining:
- What it's used for
- Which NATS account it belongs to
- Whether it has a default value

## Acceptance Criteria

- [ ] `.env.example` exists at repository root
- [ ] All 4 password variables documented with placeholder values
- [ ] Comments explain each variable's purpose
- [ ] `.env` is in `.gitignore` (already confirmed)
- [ ] README or comments reference `.env.example` as setup guide

## Implementation Notes

- `.env` is already in `.gitignore` — confirmed from current repo state
- Use `changeme` as placeholder values (not empty strings) to make missing config obvious
- Keep variable names consistent with template references in account configs
