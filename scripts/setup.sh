#!/usr/bin/env bash
# =============================================================================
# NATS Infrastructure Setup Script
# =============================================================================
# Automates the full setup sequence for the NATS infrastructure:
#   1. Validate prerequisites (docker, docker compose)
#   2. Copy .env.example to .env if it doesn't exist
#   3. Build and start services via Docker Compose
#   4. Provision JetStream streams
#   5. Verify the NATS server is healthy and streams are provisioned
#
# Usage:
#   ./scripts/setup.sh
#
# Prerequisites:
#   Required: docker, docker compose
#   Optional: jq, nats CLI (for stream provisioning)
#
# Exit codes:
#   0 — Setup completed successfully
#   1 — Setup failed (see output for details)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# ---------------------------------------------------------------------------
# Step 1: Validate prerequisites
# ---------------------------------------------------------------------------
step 1 "Validate prerequisites"

if ! command -v docker >/dev/null 2>&1; then
    error "docker is required but not installed."
    exit 1
fi
info "docker is available"

if docker compose version >/dev/null 2>&1; then
    info "docker compose is available"
else
    error "docker compose is required but not available."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 2: Environment file
# ---------------------------------------------------------------------------
step 2 "Environment file"

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
# Step 3: Build and start services
# ---------------------------------------------------------------------------
step 3 "Build and start services"

info "Running: docker compose up -d --build"
(cd "$PROJECT_ROOT" && docker compose up -d --build)
info "Docker Compose services started"

# Wait for NATS to be healthy via Docker health check
info "Waiting for NATS container to be healthy..."
MAX_WAIT=60
elapsed=0
while [[ $elapsed -lt $MAX_WAIT ]]; do
    health=$(docker inspect --format='{{.State.Health.Status}}' ships-computer-nats 2>/dev/null || echo "unknown")
    if [[ "$health" == "healthy" ]]; then
        info "NATS container is healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [[ $elapsed -ge $MAX_WAIT ]]; then
    error "NATS container did not become healthy within ${MAX_WAIT}s"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 4: Provision JetStream streams
# ---------------------------------------------------------------------------
step 4 "Provision JetStream streams"

PROVISION_SCRIPT="$PROJECT_ROOT/streams/provision-streams.sh"

if [[ -f "$PROVISION_SCRIPT" ]]; then
    if command -v nats >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
        info "Running: ./streams/provision-streams.sh"
        "$PROVISION_SCRIPT"
        info "Stream provisioning complete"
    else
        info "Skipping stream provisioning — requires nats CLI and jq"
        if ! command -v nats >/dev/null 2>&1; then
            info "  nats CLI not installed. See: https://github.com/nats-io/natscli"
        fi
        if ! command -v jq >/dev/null 2>&1; then
            info "  jq not installed. Install with: brew install jq"
        fi
    fi
else
    error "provision-streams.sh not found at $PROVISION_SCRIPT"
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 5: Verify NATS server
# ---------------------------------------------------------------------------
step 5 "Verify NATS server"

VERIFY_SCRIPT="$PROJECT_ROOT/scripts/verify-nats.sh"

if [[ -f "$VERIFY_SCRIPT" ]]; then
    info "Running: ./scripts/verify-nats.sh"
    "$VERIFY_SCRIPT"
else
    error "verify-nats.sh not found at $VERIFY_SCRIPT"
    exit 1
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "  Setup Complete"
echo "==========================================="
echo ""
echo "NATS server is running at:"
echo "  Client:  nats://localhost:4222"
echo "  Monitor: http://localhost:8222"
echo ""
