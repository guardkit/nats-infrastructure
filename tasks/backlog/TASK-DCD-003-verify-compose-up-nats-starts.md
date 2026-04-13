---
id: TASK-DCD-003
title: "Verify docker compose up - NATS starts, JetStream initialises, health check passes"
task_type: testing
parent_review: TASK-REV-1A6B
feature_id: FEAT-DCD
wave: 2
implementation_mode: direct
complexity: 2
dependencies:
  - TASK-DCD-001
  - TASK-DCD-002
status: pending
priority: high
tags: [docker, nats, testing, integration]
---

# Task: Verify Docker Compose Up

## Description

Manual and scripted verification that `docker compose up -d` successfully:
1. Builds the custom NATS image (Dockerfile)
2. Starts the NATS container (`ships-computer-nats`)
3. JetStream initialises with file-based storage at `/data/jetstream`
4. Health check endpoint responds at `http://localhost:8222/healthz`
5. Container reaches `healthy` state within 30 seconds
6. Client port 4222 accepts connections
7. Monitoring port 8222 returns server info via `/varz`

## Context

- Depends on TASK-DCD-001 (docker-compose.yml) and TASK-DCD-002 (Dockerfile)
- Requires `.env` file with valid passwords (copy from `.env.example`)
- Health check: `wget --spider -q http://localhost:8222/healthz`
- JetStream config: `max_mem: 1GB`, `max_file: 10GB`, `store_dir: /data/jetstream`

## Acceptance Criteria

- [ ] `docker compose up -d` builds and starts without errors
- [ ] Container `ships-computer-nats` reaches `healthy` state
- [ ] `curl http://localhost:8222/healthz` returns 200
- [ ] `curl http://localhost:8222/varz` returns JSON with `jetstream` config
- [ ] Port 4222 accepts TCP connections
- [ ] Container logs show "JetStream" initialisation messages
- [ ] `docker compose down` stops cleanly with no errors

## Verification Commands

```bash
# Start
docker compose up -d --build

# Check health
docker inspect --format='{{.State.Health.Status}}' ships-computer-nats

# Check JetStream
curl -sf http://localhost:8222/varz | jq '{server_name, version, jetstream}'

# Check client port
nc -z localhost 4222 && echo "OK" || echo "FAIL"

# Stop
docker compose down
```
