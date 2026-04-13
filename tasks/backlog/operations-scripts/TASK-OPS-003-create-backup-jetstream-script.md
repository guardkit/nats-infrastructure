---
id: TASK-OPS-003
title: "Create backup-jetstream.sh NAS backup script"
task_type: scaffolding
parent_review: TASK-REV-2462
feature_id: FEAT-OPS
status: pending
priority: high
complexity: 3
wave: 1
implementation_mode: direct
dependencies: []
tags: [operations, backup, jetstream, nas, rsync]
---

# Task: Create backup-jetstream.sh NAS Backup Script

## Description

Create a backup script that uses rsync to copy JetStream data from the GB10 to the Synology NAS over Tailscale. Supports timestamped backup directories and configurable retention (keep last N backups).

## Context

- JetStream data stored in Docker named volume `nats-data` mapped to `/data/jetstream`
- Synology NAS accessible via Tailscale MagicDNS at `nas.tail` (configurable)
- JetStream uses WAL-based storage — concurrent reads during rsync are safe
- Backup is incremental (rsync only transfers changed blocks)
- Non-functional requirement: automated backup to NAS for disaster recovery

## Reference

- System spec: `docs/design/specs/nats-infrastructure-system-spec.md` (Feature 5)
- Deployment target table: GB10 (NATS server), Synology NAS (backup)

## Acceptance Criteria

- [ ] Script rsyncs JetStream data directory to NAS with timestamped subdirectory (`YYYYMMDD-HHMMSS`)
- [ ] NAS hostname configurable via `BACKUP_NAS_HOST` env var (default: `nas.tail`)
- [ ] NAS backup path configurable via `BACKUP_NAS_PATH` env var (default: `/volume1/backups/nats`)
- [ ] JetStream data source configurable via `JETSTREAM_DATA_DIR` env var (default: `/data/jetstream`)
- [ ] Retention: removes backups older than N days, configurable via `BACKUP_RETAIN_DAYS` env var (default: 7)
- [ ] Pre-flight check: verifies NAS is reachable (SSH connectivity test) before starting rsync
- [ ] Post-backup verification: checks backup directory exists and reports size
- [ ] Exit code 0 = success, 1 = backup failed, 2 = NAS unreachable
- [ ] Script uses `set -euo pipefail` and `#!/bin/bash`
- [ ] Script is executable (`chmod +x`)

## Implementation Notes

The JetStream data path inside the container is `/data/jetstream`, but the Docker volume mount point on the host may differ. The script should document both approaches: direct host path access (if volume path is known) or `docker cp` from the container.
