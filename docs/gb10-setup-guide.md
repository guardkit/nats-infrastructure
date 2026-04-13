# NATS Infrastructure — Dell GB10 Setup & Verification Guide

Setup, deployment, and integration testing guide for the ships-computer NATS JetStream server on the Dell DGX Spark GB10.

---

## Prerequisites

On the GB10, ensure the following are installed:

| Tool | Purpose | Install |
|------|---------|---------|
| Docker | Container runtime | Pre-installed on DGX OS Ubuntu 24.04 |
| Docker Compose | Container orchestration | `sudo apt install docker-compose-plugin` |
| curl | Health checks / verification | Pre-installed |
| jq | JSON parsing (optional but recommended) | `sudo apt install jq` |
| nats CLI | Auth testing & pub/sub (optional) | See [natscli releases](https://github.com/nats-io/natscli/releases) |
| Git | Clone the repo | Pre-installed |
| Python 3.11+ | Run pytest suite | Pre-installed on DGX OS |

### Install the NATS CLI (recommended)

```bash
# Download latest release (check GitHub for current version)
curl -sf https://binaries.nats.dev/nats-io/natscli/nats@latest | sh

# Move to PATH
sudo mv nats /usr/local/bin/

# Verify
nats --version
```

---

## Step 1: Clone the Repository

```bash
cd ~/Projects  # or wherever you keep repos on the GB10
git clone git@github.com:appmilla/nats-infrastructure.git
cd nats-infrastructure
```

If the repo is already cloned, pull the latest:

```bash
cd ~/Projects/nats-infrastructure
git pull origin main
```

---

## Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and replace **all four** `changeme` values with strong, unique passwords:

```bash
nano .env   # or vim, your preference
```

The four required variables:

| Variable | Account | User | Access |
|----------|---------|------|--------|
| `RICH_NATS_PASSWORD` | APPMILLA | rich | Full publish/subscribe to all subjects |
| `JAMES_NATS_PASSWORD` | APPMILLA | james | Full publish/subscribe to all subjects |
| `MARK_NATS_PASSWORD` | FINPROXY | mark | Scoped to `finproxy.>` only |
| `ADMIN_NATS_PASSWORD` | SYS | admin | NATS server administration |

Generate strong passwords:

```bash
# Generate 4 random passwords
for var in RICH JAMES MARK ADMIN; do
    echo "${var}_NATS_PASSWORD=$(openssl rand -base64 24)"
done
```

Copy the output into your `.env` file.

---

## Step 3: Create the Docker Compose File

The Docker Compose file is not yet in the repository (planned for Feature 4). Create it now:

```bash
cat > docker-compose.yml << 'COMPOSE'
services:
  nats:
    image: nats:latest
    container_name: ships-computer
    restart: unless-stopped
    ports:
      - "4222:4222"   # Client connections
      - "8222:8222"   # Monitoring HTTP API
    volumes:
      - ./config:/etc/nats/config:ro
      - ./scripts/docker-entrypoint.sh:/docker-entrypoint.sh:ro
      - nats-jetstream:/data/jetstream
      - nats-logs:/var/log/nats
    entrypoint: ["/docker-entrypoint.sh"]
    command: ["-c", "/etc/nats/nats-server.conf"]
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

volumes:
  nats-jetstream:
    driver: local
  nats-logs:
    driver: local
COMPOSE
```

---

## Step 4: Start the NATS Server

```bash
docker compose up -d
```

Check that the container started:

```bash
docker compose ps
```

Expected output:

```
NAME              IMAGE         COMMAND                  SERVICE   STATUS
ships-computer    nats:latest   "/docker-entrypoint.…"  nats      Up X seconds (healthy)
```

Check the entrypoint processed the account templates:

```bash
docker compose logs nats
```

You should see lines like:

```
Processed: /etc/nats/config/accounts/accounts.conf.template -> /etc/nats/accounts/accounts.conf
```

---

## Step 5: Run the Verification Script

```bash
./scripts/verify-nats.sh
```

If passwords are set in your shell environment (not just `.env`), the script will also test account authentication. To enable this:

```bash
source .env
./scripts/verify-nats.sh
```

Expected output:

```
=============================================
  NATS Server Verification
=============================================

Monitor URL: http://localhost:8222
Timeout: 30s

Waiting for NATS server to be ready...
NATS server is responding.

--- Check 1: Health Endpoint ---
  [PASS] Health endpoint returned HTTP 200

--- Check 2: JetStream Status ---
  [PASS] JetStream is initialised (memory/storage info present)

--- Check 3: Server Info ---
  [PASS] server_name is 'ships-computer'
  [PASS] NATS server version: X.X.X

--- Check 4: Account Authentication (Optional) ---
  [PASS] APPMILLA user 'rich' can connect and publish
  [PASS] FINPROXY user 'mark' can connect with scoped access

=============================================
  Results: 6 passed, 0 failed
=============================================
  All checks PASSED
```

---

## Step 6: Manual Smoke Tests

These are quick manual checks you can run to confirm things are working beyond the verification script.

### 6.1 Check monitoring endpoints directly

```bash
# Health
curl -sf http://localhost:8222/healthz && echo " OK"

# Server info
curl -sf http://localhost:8222/varz | jq '{server_name, version, host, port, max_payload}'

# JetStream info
curl -sf http://localhost:8222/jsz | jq '{memory, store, streams, consumers}'

# Connections
curl -sf http://localhost:8222/connz | jq '{num_connections, connections}'
```

### 6.2 Test pub/sub with the NATS CLI

Requires the `nats` CLI and passwords sourced into your shell:

```bash
source .env
```

**Test APPMILLA full access (rich):**

```bash
# Terminal 1 — subscribe
nats sub "test.>" --user rich --password "$RICH_NATS_PASSWORD"

# Terminal 2 — publish
nats pub test.hello "Hello from GB10" --user rich --password "$RICH_NATS_PASSWORD"
```

You should see the message arrive in Terminal 1.

**Test FINPROXY scoped access (mark):**

```bash
# Should succeed — within finproxy.> scope
nats pub finproxy.test "Hello from FinProxy" --user mark --password "$MARK_NATS_PASSWORD"

# Should FAIL — outside finproxy.> scope (permissions violation)
nats pub pipeline.test "Should fail" --user mark --password "$MARK_NATS_PASSWORD"
```

The second command should produce a permissions error, confirming account isolation is working.

### 6.3 Test JetStream persistence

```bash
# Create a test stream
nats stream add TEST \
    --subjects "test.>" \
    --storage file \
    --retention limits \
    --max-msgs 1000 \
    --max-age 1h \
    --user rich --password "$RICH_NATS_PASSWORD"

# Publish a message
nats pub test.jetstream "Persistent message" --user rich --password "$RICH_NATS_PASSWORD"

# Check the stream has the message
nats stream info TEST --user rich --password "$RICH_NATS_PASSWORD"

# Clean up
nats stream rm TEST --force --user rich --password "$RICH_NATS_PASSWORD"
```

---

## Step 7: Run the Pytest Suite

The pytest suite validates configuration files, scripts, and templates. Run it from your development machine or from the GB10 if Python is available.

```bash
# Install test dependencies (one-time)
pip install pytest

# Run all tests
pytest tests/ -v
```

Expected: 89 tests, all passing. These tests validate the static configuration — they do not require a running NATS server.

---

## Step 8: Integration Testing Against the Live Server

These tests verify the running NATS server end-to-end. You can run them from any machine that can reach the GB10 on ports 4222 and 8222 (e.g. over Tailscale).

### 8.1 From a remote machine via Tailscale

Replace `<GB10_TAILSCALE_IP>` with the GB10's Tailscale IP address:

```bash
# Health check
curl -sf http://<GB10_TAILSCALE_IP>:8222/healthz && echo " OK"

# Server info
curl -sf http://<GB10_TAILSCALE_IP>:8222/varz | jq '{server_name, version}'

# Pub/sub test
nats pub test.remote "Hello from remote" \
    --server "nats://<GB10_TAILSCALE_IP>:4222" \
    --user rich --password "$RICH_NATS_PASSWORD"
```

### 8.2 Run the verification script against a remote server

```bash
NATS_MONITOR_URL="http://<GB10_TAILSCALE_IP>:8222" ./scripts/verify-nats.sh
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker compose logs nats

# Common issue: missing passwords
# Look for: "ERROR: Missing required environment variables"
# Fix: ensure all 4 passwords are set in .env
```

### Health check fails

```bash
# Check if the container is running
docker compose ps

# Check if port 8222 is listening
ss -tlnp | grep 8222

# Try hitting the endpoint manually
curl -v http://localhost:8222/healthz
```

### JetStream not initialised

```bash
# Check JetStream storage directory exists inside the container
docker compose exec nats ls -la /data/jetstream

# Check NATS logs for JetStream errors
docker compose exec nats cat /var/log/nats/nats-server.log | grep -i jetstream
```

### Account authentication fails

```bash
# Verify the template was processed correctly
docker compose exec nats cat /etc/nats/accounts/accounts.conf

# Check there are no leftover ${VAR} placeholders
docker compose exec nats grep '${' /etc/nats/accounts/accounts.conf
# This should return nothing — all variables should be substituted
```

### Permissions error for FINPROXY user

This is expected behaviour. The FINPROXY account (user: mark) is scoped to `finproxy.>` subjects only. Publishing to any other subject will produce a permissions violation — this confirms account isolation is working correctly.

---

## Stopping and Restarting

```bash
# Stop (preserves data volumes)
docker compose down

# Stop and remove volumes (DESTROYS JetStream data)
docker compose down -v

# Restart
docker compose restart nats

# View live logs
docker compose logs -f nats
```

---

## Quick Reference

| What | Command |
|------|---------|
| Start server | `docker compose up -d` |
| Stop server | `docker compose down` |
| View logs | `docker compose logs -f nats` |
| Run verification | `./scripts/verify-nats.sh` |
| Run pytest suite | `pytest tests/ -v` |
| Health check | `curl -sf http://localhost:8222/healthz` |
| Server info | `curl -sf http://localhost:8222/varz \| jq .` |
| JetStream info | `curl -sf http://localhost:8222/jsz \| jq .` |
| Publish (APPMILLA) | `nats pub test.msg "hello" --user rich --password $RICH_NATS_PASSWORD` |
| Publish (FINPROXY) | `nats pub finproxy.msg "hello" --user mark --password $MARK_NATS_PASSWORD` |
