#!/usr/bin/env bash
# =============================================================================
# NATS Infrastructure — GB10 One-Shot Setup Script
# =============================================================================
# Automates the full setup sequence for deploying NATS infrastructure on the
# Dell DGX Spark GB10 (128GB, Ubuntu 24.04).
#
# Setup sequence:
#   1. Validate prerequisites (docker, docker compose, curl)
#   2. Install NATS CLI if not present
#   3. Copy .env.example to .env if it doesn't exist
#   4. Build and start services via Docker Compose
#   5. Wait for NATS to be healthy
#   6. Provision JetStream streams
#   7. Provision KV buckets
#   8. Verify the NATS server (including KV bucket listing)
#
# Usage:
#   ./scripts/setup-gb10.sh
#
# Prerequisites:
#   Required: docker, docker compose, curl
#   Optional: jq (installed automatically if missing on Ubuntu)
#
# Environment variables:
#   NATS_URL             — NATS client URL (default: nats://localhost:4222)
#   NATS_MONITOR_URL     — NATS monitoring URL (default: http://localhost:8222)
#   HEALTH_TIMEOUT       — Seconds to wait for NATS health (default: 60)
#
# Exit codes:
#   0 — Setup completed successfully
#   1 — Setup failed (see output for details)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration with environment variable overrides
NATS_URL="${NATS_URL:-nats://localhost:4222}"
NATS_MONITOR_URL="${NATS_MONITOR_URL:-http://localhost:8222}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

step() {
    echo ""
    echo "==========================================="
    echo "  Step $1: $2"
    echo "==========================================="
}

info() {
    echo "  [INFO] $1"
}

error() {
    echo "  [ERROR] $1" >&2
}

has_command() {
    command -v "$1" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Step 1: Validate prerequisites
# ---------------------------------------------------------------------------
step 1 "Validate prerequisites"

if ! has_command docker; then
    error "docker is required but not installed."
    error "Install: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi
info "docker is available"

if docker compose version >/dev/null 2>&1; then
    info "docker compose is available"
else
    error "docker compose is required but not available."
    error "Install: sudo apt install docker-compose-plugin"
    exit 1
fi

if ! has_command curl; then
    error "curl is required but not installed."
    error "Install: sudo apt install curl"
    exit 1
fi
info "curl is available"

# jq is recommended but not blocking for setup
if has_command jq; then
    info "jq is available"
else
    info "jq not found — stream/KV provisioning requires jq"
    info "Install: sudo apt install jq"
fi

# ---------------------------------------------------------------------------
# Step 2: Install NATS CLI if not present
# ---------------------------------------------------------------------------
step 2 "Install NATS CLI"

if has_command nats; then
    info "nats CLI is already installed: $(nats --version 2>/dev/null || echo 'unknown version')"
else
    info "Installing NATS CLI via official installer..."
    if curl -sf https://binaries.nats.dev/nats-io/natscli/nats@latest | sh; then
        if [[ -f ./nats ]]; then
            sudo mv ./nats /usr/local/bin/
            info "NATS CLI installed to /usr/local/bin/nats"
        else
            error "NATS CLI binary not found after install"
            info "Continuing without nats CLI — provisioning will be skipped"
        fi
    else
        error "Failed to install NATS CLI"
        info "Continuing without nats CLI — provisioning will be skipped"
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: Environment file
# ---------------------------------------------------------------------------
step 3 "Environment file"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    info ".env file already exists — skipping copy"
else
    if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        info "Copied .env.example to .env"
        info "IMPORTANT: Edit .env with real passwords before production use"
    else
        error ".env.example not found — cannot create .env"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Step 4: Build and start services
# ---------------------------------------------------------------------------
step 4 "Build and start services"

# Check if the container is already running
CONTAINER_NAME="ships-computer-nats"
if docker inspect --format='{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "true"; then
    info "NATS container '$CONTAINER_NAME' is already running — skipping docker compose up"
else
    info "Running: docker compose up -d --build"
    (cd "$PROJECT_ROOT" && docker compose up -d --build)
    info "Docker Compose services started"
fi

# ---------------------------------------------------------------------------
# Step 5: Wait for NATS to be healthy
# ---------------------------------------------------------------------------
step 5 "Wait for NATS to be healthy"

info "Waiting for NATS container to be healthy (timeout: ${HEALTH_TIMEOUT}s)..."
elapsed=0
while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
    health=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
    if [[ "$health" == "healthy" ]]; then
        info "NATS container is healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [[ $elapsed -ge $HEALTH_TIMEOUT ]]; then
    error "NATS container did not become healthy within ${HEALTH_TIMEOUT}s"
    exit 1
fi

# Also verify the health endpoint directly
if curl -sS --max-time 5 "${NATS_MONITOR_URL}/healthz" >/dev/null 2>&1; then
    info "NATS health endpoint responding at ${NATS_MONITOR_URL}/healthz"
else
    error "NATS health endpoint not responding at ${NATS_MONITOR_URL}/healthz"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 6: Provision JetStream streams
# ---------------------------------------------------------------------------
step 6 "Provision JetStream streams"

PROVISION_STREAMS_SCRIPT="$PROJECT_ROOT/streams/provision-streams.sh"

if [[ -f "$PROVISION_STREAMS_SCRIPT" ]]; then
    if has_command nats && has_command jq; then
        info "Running: ./streams/provision-streams.sh"
        "$PROVISION_STREAMS_SCRIPT"
        info "Stream provisioning complete"
    else
        info "Skipping stream provisioning — requires nats CLI and jq"
        if ! has_command nats; then
            info "  nats CLI not installed. See: https://github.com/nats-io/natscli"
        fi
        if ! has_command jq; then
            info "  jq not installed. Install with: sudo apt install jq"
        fi
    fi
else
    info "provision-streams.sh not found at $PROVISION_STREAMS_SCRIPT — skipping"
    info "Streams can be provisioned later with: ./streams/provision-streams.sh"
fi

# ---------------------------------------------------------------------------
# Step 7: Provision KV buckets
# ---------------------------------------------------------------------------
step 7 "Provision KV buckets"

PROVISION_KV_SCRIPT="$PROJECT_ROOT/kv/provision-kv.sh"

if [[ -f "$PROVISION_KV_SCRIPT" ]]; then
    if has_command nats && has_command jq; then
        info "Running: ./kv/provision-kv.sh"
        if "$PROVISION_KV_SCRIPT"; then
            info "KV bucket provisioning complete"
        else
            error "KV bucket provisioning failed"
            exit 1
        fi
    else
        info "Skipping KV provisioning — requires nats CLI and jq"
        if ! has_command nats; then
            info "  nats CLI not installed. See: https://github.com/nats-io/natscli"
        fi
        if ! has_command jq; then
            info "  jq not installed. Install with: sudo apt install jq"
        fi
    fi
else
    error "provision-kv.sh not found at $PROVISION_KV_SCRIPT"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 8: Verify NATS server
# ---------------------------------------------------------------------------
step 8 "Verify NATS server"

VERIFY_SCRIPT="$PROJECT_ROOT/scripts/verify-nats.sh"

if [[ -f "$VERIFY_SCRIPT" ]]; then
    info "Running: ./scripts/verify-nats.sh"
    "$VERIFY_SCRIPT"
else
    error "verify-nats.sh not found at $VERIFY_SCRIPT"
    exit 1
fi

# Additional KV bucket verification
if has_command nats; then
    info ""
    info "--- KV Bucket Verification ---"
    info "Running: nats kv ls"
    if nats kv ls --server "$NATS_URL" 2>/dev/null; then
        info "KV bucket listing complete"
    else
        info "KV bucket listing failed — buckets may not be provisioned"
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "  GB10 Setup Complete"
echo "==========================================="
echo ""
echo "NATS server is running at:"
echo "  Client:  ${NATS_URL}"
echo "  Monitor: ${NATS_MONITOR_URL}"
echo ""
