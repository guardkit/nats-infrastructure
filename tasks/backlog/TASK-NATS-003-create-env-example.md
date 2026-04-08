---
id: TASK-NATS-003
title: "Create .env.example with all configuration variables"
status: pending
task_type: scaffolding
parent_review: TASK-REV-69BD
feature_id: FEAT-NATS-CFG
wave: 3
implementation_mode: direct
complexity: 2
dependencies:
  - TASK-NATS-002
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
