---
id: TASK-NATS-001
title: "Create nats-server.conf with JetStream enabled"
status: pending
task_type: scaffolding
parent_review: TASK-REV-69BD
feature_id: FEAT-NATS-CFG
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
---

# Create nats-server.conf with JetStream Enabled

## Description

Create the main NATS server configuration file at `config/nats-server.conf` for deployment on Dell DGX Spark GB10 (128GB). The config must enable JetStream with file-based storage, configure client connections on port 4222, monitoring on port 8222, and bind to all interfaces for Tailscale mesh VPN access.

## Requirements

Based on system spec Feature 1 and review findings (TASK-REV-69BD):

- Server name: `ships-computer`
- Client port: 4222, bound to `0.0.0.0`
- Monitoring HTTP port: 8222, bound to `0.0.0.0`
- Max payload: 1MB
- JetStream enabled with:
  - `store_dir: "/data/jetstream"`
  - `max_mem: 1GB`
  - `max_file: 10GB`
- Logging to `/var/log/nats/nats-server.log` with timestamps
- Include directive for `accounts/*.conf`
- Debug and trace disabled by default

## Acceptance Criteria

- [ ] `config/nats-server.conf` exists with all settings from requirements
- [ ] JetStream block configured with store_dir, max_mem, max_file
- [ ] Server listens on 0.0.0.0:4222 (client) and 0.0.0.0:8222 (monitoring)
- [ ] Include directive references `accounts/*.conf`
- [ ] Config file has clear comments explaining each section
- [ ] Config syntax is valid NATS server configuration format

## Implementation Notes

- Use NATS native config format (not JSON or YAML)
- Create `config/` directory if it doesn't exist
- The `include` path is relative to the config file location in the container (`/etc/nats/`)
- JetStream `max_mem: 1GB` is conservative for 128GB GB10 — leaves headroom for GPU workloads
- `max_file: 10GB` covers all 7 streams with 7-day retention
